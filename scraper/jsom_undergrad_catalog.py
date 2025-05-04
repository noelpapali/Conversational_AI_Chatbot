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

# Output directory and file
output_dir = config.get('DEFAULT', '../scraped_data',fallback="../scraped_data")
output_file = os.path.join(output_dir, "jsom_undergrad_catalog_data.txt")

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
    content_blocks = soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "li", "a"])

    headings = []
    paragraphs = []
    lists = []
    links = []

    for tag in content_blocks:
        if tag.name in ["h1", "h2", "h3"]:
            headings.append(tag.get_text(strip=True))
        elif tag.name == "p":
            paragraphs.append(tag.get_text(strip=True))
        elif tag.name in ["ul", "ol"]:
            for li in tag.find_all("li"):
                lists.append(li.get_text(strip=True))
        elif tag.name == "a" and tag.has_attr("href"):
            links.append(f"{tag.get_text(strip=True)} - {tag['href']}")

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

    # List of new undergrad and admission URLs
    urls = [
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/accounting",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/business-administration",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/business-analytics",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/finance",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/global-business",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/healthcare-management",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/human-resource-management",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/marketing",
        "https://catalog.utdallas.edu/2024/undergraduate/programs/jsom/supply-chain-management",
        "https://coursebook.utdallas.edu/search/now/math1325",
        "https://enroll.utdallas.edu/transfer/criteria/",
        "https://enroll.utdallas.edu/freshman/"
    ]

    # Open the output file to write the scraped data
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Opened file for writing: {output_file}")

            # Scrape each page
            for url in urls:
                logging.info(f"Scraping page: {url}")
                page_content = fetch_webpage(url)
                if not page_content:
                    continue

                soup = BeautifulSoup(page_content, "html.parser")
                scraped_data = scrape_general_page(soup, url)

                for data in scraped_data:
                    write_to_txt(file, data)

                time.sleep(REQUEST_DELAY)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except IOError as e:
        logging.error(f"Failed to write to file {output_file}: {e}")


if __name__ == "__main__":
    main()