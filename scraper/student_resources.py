import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser
import time

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the main page to scrape
main_page_url = config.get('DEFAULT', 'main_page_url', fallback="https://jindal.utdallas.edu/student-resources/")

# Output directory and file
output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
output_file = os.path.join(output_dir, "student_resources_data.txt")

# Rate limiting delay
REQUEST_DELAY = int(config.get('DEFAULT', 'request_delay', fallback=2))

# User-Agent header to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def create_output_directory():
    """Create the output directory if it doesn't exist."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created output directory: {output_dir}")


def fetch_webpage(url):
    """Fetch the content of a webpage."""
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None


def scrape_student_resources_page(soup, url):
    """Scrape the student resources page."""
    content = []
    stat_containers = soup.find_all("div", class_="stat-container")
    for container in stat_containers:
        stat_boxes = container.find_all("div", class_="stat-box")
        for box in stat_boxes:
            title = box.find("h3").get_text(strip=True) if box.find("h3") else "No Title"
            paragraphs = [p.get_text(strip=True) for p in box.find_all("p")]
            content.append({
                "url": url,
                "title": title,
                "content": paragraphs
            })
    return content


def scrape_advising_page(soup, url):
    """Scrape the advising page."""
    content = []
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        headings = [h2.get_text(strip=True) for h2 in block.find_all("h2")]
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
        content.append({
            "url": url,
            "headings": headings,
            "content": paragraphs
        })
    return content


def scrape_scholarships_page(soup, url):
    """Scrape the scholarships page."""
    content = []
    wideblock = soup.find("div", class_="wideblock overflow")
    if wideblock:
        headings = [h2.get_text(strip=True) for h2 in wideblock.find_all(["h2", "h3"])]
        paragraphs = [p.get_text(strip=True) for p in wideblock.find_all("p")]
        links = [a.get_text(strip=True) + " - " + a['href'] for a in wideblock.find_all("a", class_="cta-link")]
        content.append({
            "url": url,
            "headings": headings,
            "content": paragraphs,
            "links": links
        })
    return content


def scrape_assistantships_page(soup, url):
    """Scrape the assistantships page."""
    content = []
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        headings = [h2.get_text(strip=True) for h2 in block.find_all("h2")]
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
        lists = [li.get_text(strip=True) for li in block.find_all("li")]
        content.append({
            "url": url,
            "headings": headings,
            "content": paragraphs,
            "lists": lists
        })
    return content


def scrape_student_organizations_page(soup, url):
    """Scrape the student organizations page."""
    content = []
    entry_content = soup.find("div", class_="entry-content")
    if entry_content:
        paragraphs = [p.get_text(strip=True) for p in entry_content.find_all("p")]
        links = [a.get_text(strip=True) + " - " + a['href'] for a in entry_content.find_all("a")]
        content.append({
            "url": url,
            "content": paragraphs,
            "links": links
        })
    return content


def scrape_labs_page(soup, url):
    """Scrape the labs page, ensuring both wideblock overflow and tab-content are scraped."""
    content = []

    # Scrape wideblock overflow divs (existing functionality)
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        headings = [h2.get_text(strip=True) for h2 in block.find_all("h2")]
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
        lists = [li.get_text(strip=True) for li in block.find_all("li")]
        links = [a.get_text(strip=True) + " - " + a["href"] for a in block.find_all("a", href=True)]

        content.append({
            "url": url,
            "title": "No Title",  # Default title for wideblock content
            "headings": headings,
            "content": paragraphs,
            "lists": lists,
            "links": links
        })

    # Scrape tabbed content (new functionality)
    tab_headers = soup.find_all("button", class_="tab-header")
    tab_contents = soup.find_all("div", class_="tab-content")

    for header, tab_content in zip(tab_headers, tab_contents):
        # Extract the tab title
        title = header.find("h3").get_text(strip=True) if header.find("h3") else "No Title"

        # Extract content from the tab
        tab_data = {
            "url": url,
            "title": title,
            "headings": [],
            "content": [],
            "lists": [],
            "links": []
        }

        # Extract headings (h4)
        headings = tab_content.find_all("h4")
        tab_data["headings"] = [h.get_text(strip=True) for h in headings]

        # Extract paragraphs (p)
        paragraphs = tab_content.find_all("p")
        tab_data["content"] = [p.get_text(strip=True) for p in paragraphs]

        # Extract lists (ul > li)
        lists = tab_content.find_all("ul")
        for ul in lists:
            tab_data["lists"].extend([li.get_text(strip=True) for li in ul.find_all("li")])

        # Extract links (a)
        links = tab_content.find_all("a", href=True)
        tab_data["links"] = [a.get_text(strip=True) + " - " + a["href"] for a in links]

        # Append the tab data to the content list
        content.append(tab_data)

    return content


def scrape_business_communication_center(soup, url):
    """Scrape the Business Communication Center page."""
    content = []

    # Scrape wideblock overflow divs
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        # Extract headings (h2, h3, h4, etc.)
        headings = [h.get_text(strip=True) for h in block.find_all(["h2", "h3", "h4"])]

        # Extract paragraphs (p)
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]

        # Extract lists (ul > li)
        lists = [li.get_text(strip=True) for li in block.find_all("li")]

        # Extract links (a)
        links = [a.get_text(strip=True) + " - " + a["href"] for a in block.find_all("a", href=True)]

        # Append the scraped data
        content.append({
            "url": url,
            "headings": headings,
            "content": paragraphs,
            "lists": lists,
            "links": links
        })

    return content


def scrape_policies_faq(soup, url):
    """Scrape the Policies and FAQ page."""
    content = []

    # Scrape FAQ sections
    faq_sections = soup.find_all("div", class_="smallblock white overflow")
    for section in faq_sections:
        # Extract section title (h3)
        title = section.find("h3").get_text(strip=True) if section.find("h3") else "No Title"

        # Extract questions and answers
        questions = []
        answers = []

        # Find all tab headers (questions) and tab content (answers)
        tab_headers = section.find_all("button", class_="tab-header")
        tab_contents = section.find_all("div", class_="tab-content")

        for header, tab_content in zip(tab_headers, tab_contents):
            # Extract question
            question = header.find("h3").get_text(strip=True) if header.find("h3") else "No Question"
            questions.append(question)

            # Extract answer
            answer = tab_content.get_text(strip=True) if tab_content else "No Answer"
            answers.append(answer)

        # Append the scraped data
        content.append({
            "url": url,
            "title": title,
            "questions": questions,
            "answers": answers
        })

    return content


def scrape_deans_council(soup, url):
    """Scrape the Dean’s Council page."""
    content = []

    # Scrape wideblock overflow divs
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        # Extract headings (h2, h3, h4, etc.)
        headings = [h.get_text(strip=True) for h in block.find_all(["h2", "h3", "h4"])]

        # Extract paragraphs (p)
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]

        # Extract lists (ul > li)
        lists = [li.get_text(strip=True) for li in block.find_all("li")]

        # Extract links (a)
        links = [a.get_text(strip=True) + " - " + a["href"] for a in block.find_all("a", href=True)]

        # Append the scraped data
        content.append({
            "url": url,
            "headings": headings,
            "content": paragraphs,
            "lists": lists,
            "links": links
        })

    return content


def write_to_txt(file, data):
    """Write scraped data to a text file."""
    file.write(f"URL: {data['url']}\n")
    if "title" in data:
        file.write(f"Title: {data['title']}\n")
    if "headings" in data:
        file.write("Headings:\n")
        for heading in data['headings']:
            file.write(f"- {heading}\n")
    if "content" in data:
        file.write("Content:\n")
        for paragraph in data['content']:
            file.write(f"{paragraph}\n")
    if "lists" in data:
        file.write("Lists:\n")
        for item in data['lists']:
            file.write(f"- {item}\n")
    if "links" in data:
        file.write("Links:\n")
        for link in data['links']:
            file.write(f"- {link}\n")
    if "questions" in data and "answers" in data:
        file.write("Questions and Answers:\n")
        for question, answer in zip(data['questions'], data['answers']):
            file.write(f"Q: {question}\nA: {answer}\n")
    file.write("\n" + "=" * 80 + "\n")


def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # List of pages to scrape
    pages = [
        {
            "url": "https://jindal.utdallas.edu/student-resources/",
            "scrape_function": scrape_student_resources_page
        },
        {
            "url": "https://jindal.utdallas.edu/advising/",
            "scrape_function": scrape_advising_page
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/scholarships/",
            "scrape_function": scrape_scholarships_page
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/assistantships/",
            "scrape_function": scrape_assistantships_page
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/student-organizations/",
            "scrape_function": scrape_student_organizations_page
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/labs/",
            "scrape_function": scrape_labs_page
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/business-communication-center/",
            "scrape_function": scrape_business_communication_center
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/business-communication-center/policies-and-faq/",
            "scrape_function": scrape_policies_faq
        },
        {
            "url": "https://jindal.utdallas.edu/student-resources/deans-council/",
            "scrape_function": scrape_deans_council
        }
    ]

    # Open the output file to write the scraped data
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Opened file for writing: {output_file}")

            # Scrape each page
            for page in pages:
                url = page["url"]
                scrape_function = page["scrape_function"]
                logging.info(f"Scraping page: {url}")

                # Fetch the page content
                page_content = fetch_webpage(url)
                if not page_content:
                    continue

                # Parse the page HTML
                soup = BeautifulSoup(page_content, "html.parser")

                # Scrape the page using the appropriate function
                scraped_data = scrape_function(soup, url)

                # Write the scraped data to the file
                for data in scraped_data:
                    write_to_txt(file, data)

                # Respect rate limiting
                time.sleep(REQUEST_DELAY)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except IOError as e:
        logging.error(f"Failed to write to file {output_file}: {e}")


if __name__ == "__main__":
    main()