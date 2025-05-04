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

# URL of the main page to scrape
main_page_url = config.get('DEFAULT', 'main_page_url', fallback="https://jindal.utdallas.edu/admission-requirements/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'scraped_data', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "admission_requirements_data.txt")

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


def scrape_general_page(soup, url):
    """Scrape a general page with structured data extraction."""
    try:
        content = []
        wideblocks = soup.find_all("div", class_="wideblock overflow")

        for block in wideblocks:
            headings = [h2.get_text(strip=True) for h2 in block.find_all(["h2", "h3", "h4"])]
            paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
            lists = [li.get_text(strip=True) for li in block.find_all("li")]
            links = [f"{a.get_text(strip=True)} - {urljoin(url, a['href'])}"
                     for a in block.find_all("a", href=True)]

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

        # List of pages to scrape
        pages = [
            {"url": "https://jindal.utdallas.edu/admission-requirements/", "scrape_function": scrape_general_page},
            {"url": "https://jindal.utdallas.edu/admission-requirements/undergraduate/",
             "scrape_function": scrape_general_page},
            {"url": "https://jindal.utdallas.edu/admission-requirements/masters/",
             "scrape_function": scrape_general_page},
            {"url": "https://mba.utdallas.edu/admissions/?_ga=2.151205625.1711926295.1745296287-648351428.1729873009",
             "scrape_function": scrape_general_page},
            {"url": "https://jindal.utdallas.edu/phd-programs/admission-requirements/",
             "scrape_function": scrape_general_page},
            {"url": "https://enroll.utdallas.edu/", "scrape_function": scrape_general_page},
            {
                "url": "https://jindal.utdallas.edu/undergraduate-programs/prospective-undergraduates/?_ga=2.31430911.1730077543.1617027628-190102431.1606368389#02-apply-now",
                "scrape_function": scrape_general_page}
        ]

        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")

            for page in pages:
                url = page["url"]
                logging.info(f"Processing page: {url}")

                page_content = fetch_webpage(url)
                if not page_content:
                    continue

                soup = BeautifulSoup(page_content, "html.parser")
                scraped_data = page["scrape_function"](soup, url)

                for data in scraped_data:
                    write_to_txt(file, data)

                time.sleep(REQUEST_DELAY)

        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise


if __name__ == "__main__":
    main()