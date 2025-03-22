import os
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

# URL of the page to scrape
url = "https://jindal.utdallas.edu/centers-of-excellence/"

# Output directory and file
output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
output_file = os.path.join(output_dir, "centers_of_excellence_data.txt")

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


def scrape_main_heading(soup, url):
    """Scrape the main heading (h1) from the page."""
    main_heading = soup.find("div", class_="entry-title")
    if main_heading:
        return {
            "url": url,
            "title": main_heading.get_text(strip=True),
            "content": [],
            "lists": [],
            "links": []
        }
    return None


def scrape_wideblock_content(soup, url):
    """Scrape content from wideblock overflow divs."""
    content = []
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


def scrape_stat_boxes(soup, url):
    """Scrape content from stat-box divs."""
    content = []
    stat_boxes = soup.find_all("div", class_="stat-box")
    for box in stat_boxes:
        # Extract headings (h2, h3, h4, etc.)
        headings = [h.get_text(strip=True) for h in box.find_all(["h2", "h3", "h4"])]

        # Extract paragraphs (p)
        paragraphs = [p.get_text(strip=True) for p in box.find_all("p")]

        # Extract lists (ul > li)
        lists = [li.get_text(strip=True) for li in box.find_all("li")]

        # Extract links (a)
        links = [a.get_text(strip=True) + " - " + a["href"] for a in box.find_all("a", href=True)]

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
    file.write("\n" + "=" * 80 + "\n")


def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    logging.info(f"Scraping page: {url}")

    # Fetch the page content
    page_content = fetch_webpage(url)
    if not page_content:
        return

    # Parse the page HTML
    soup = BeautifulSoup(page_content, "html.parser")

    # Scrape the main heading
    main_heading_data = scrape_main_heading(soup, url)
    if main_heading_data:
        logging.info("Scraped main heading.")

    # Scrape wideblock content
    wideblock_data = scrape_wideblock_content(soup, url)
    logging.info(f"Scraped {len(wideblock_data)} wideblock sections.")

    # Scrape stat-box content
    stat_box_data = scrape_stat_boxes(soup, url)
    logging.info(f"Scraped {len(stat_box_data)} stat-box sections.")

    # Combine all scraped data
    scraped_data = []
    if main_heading_data:
        scraped_data.append(main_heading_data)
    scraped_data.extend(wideblock_data)
    scraped_data.extend(stat_box_data)

    # Open the output file to write the scraped data
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Opened file for writing: {output_file}")

            # Write the scraped data to the file
            for data in scraped_data:
                write_to_txt(file, data)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except IOError as e:
        logging.error(f"Failed to write to file {output_file}: {e}")


if __name__ == "__main__":
    main()