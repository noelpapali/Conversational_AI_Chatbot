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
main_page_url = config.get('DEFAULT', 'main_page_url', fallback="https://jindal.utdallas.edu/admission-requirements/")

# Output directory and file
output_dir = config.get('DEFAULT', 'scraped_data',fallback="../scraped_data")
output_file = os.path.join(output_dir, "admission_requirements_data.txt")

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

def scrape_general_page(soup, url):
    """Scrape a general page."""
    content = []
    wideblocks = soup.find_all("div", class_="wideblock overflow")
    for block in wideblocks:
        headings = [h2.get_text(strip=True) for h2 in block.find_all(["h2", "h3", "h4"])]
        paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
        lists = [li.get_text(strip=True) for li in block.find_all("li")]
        links = [a.get_text(strip=True) + " - " + a["href"] for a in block.find_all("a", href=True)]
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

    # List of pages to scrape
    pages = [
        {
            "url": "https://jindal.utdallas.edu/admission-requirements/",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://jindal.utdallas.edu/admission-requirements/undergraduate/",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://jindal.utdallas.edu/admission-requirements/masters/",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://mba.utdallas.edu/admissions/?_ga=2.151205625.1711926295.1745296287-648351428.1729873009",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://jindal.utdallas.edu/phd-programs/admission-requirements/",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://enroll.utdallas.edu/",
            "scrape_function": scrape_general_page
        },
        {
            "url": "https://jindal.utdallas.edu/undergraduate-programs/prospective-undergraduates/?_ga=2.31430911.1730077543.1617027628-190102431.1606368389#02-apply-now",
            "scrape_function": scrape_general_page
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