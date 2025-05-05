import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Determine environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the page to scrape
page_url = config.get('DEFAULT', 'page_url', fallback="https://bursar.utdallas.edu/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'scraped_data', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "bursar_data.txt")

# Rate limiting delay
REQUEST_DELAY = int(config.get('DEFAULT', 'request_delay', fallback=2))

# User-Agent header to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def create_output_directory():
    """Create the output directory if it doesn't exist."""
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
    except Exception as e:
        logging.error(f"Failed to create directory {output_dir}: {e}")
        raise


def fetch_webpage(url):
    """Fetch the content of a webpage with error handling."""
    try:
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None


def scrape_bursar_page(soup, url):
    """Scrape the bursar page with structured data extraction."""
    try:
        content = []
        main_content = soup.find("div", role="main") or soup

        # Extract all relevant sections
        sections = main_content.find_all(["div", "section"], class_=["content", "main-content", "entry-content"])

        for section in sections:
            headings = [h.get_text(strip=True) for h in section.find_all(["h1", "h2", "h3", "h4"])]
            paragraphs = [p.get_text(strip=True) for p in section.find_all("p")]
            lists = [li.get_text(strip=True) for li in section.find_all("li")]
            links = [f"{a.get_text(strip=True)} - {urljoin(url, a['href'])}"
                     for a in section.find_all("a", href=True)]

            content.append({
                "url": url,
                "headings": headings,
                "content": paragraphs,
                "lists": lists,
                "links": links
            })

        return content
    except Exception as e:
        logging.error(f"Error scraping page {url}: {e}")
        return []


def write_to_txt(file, data):
    """Write scraped data to a text file with proper formatting."""
    try:
        file.write(f"URL: {data['url']}\n")
        if data.get('headings'):
            file.write("Headings:\n")
            for heading in data['headings']:
                file.write(f"- {heading}\n")
        if data.get('content'):
            file.write("Content:\n")
            for paragraph in data['content']:
                file.write(f"{paragraph}\n")
        if data.get('lists'):
            file.write("Lists:\n")
            for item in data['lists']:
                file.write(f"- {item}\n")
        if data.get('links'):
            file.write("Links:\n")
            for link in data['links']:
                file.write(f"- {link}\n")
        file.write("\n" + "=" * 80 + "\n")
    except Exception as e:
        logging.error(f"Error writing data to file: {e}")


def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Scrape the main page
        page_content = fetch_webpage(page_url)
        if not page_content:
            raise RuntimeError("Failed to fetch main page content")

        soup = BeautifulSoup(page_content, "html.parser")
        scraped_data = scrape_bursar_page(soup, page_url)

        # Write all scraped data to file
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")
            for data in scraped_data:
                write_to_txt(file, data)

        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise


if __name__ == "__main__":
    main()