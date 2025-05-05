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

# Determine environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the page to scrape
url = config.get('DEFAULT', 'faculty_url', fallback="https://jindal.utdallas.edu/faculty/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "faculty_page_data.txt")

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
    """Fetch the content of a webpage."""
    try:
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def scrape_faculty_page(soup, url):
    """Scrape the Faculty page."""
    content = []

    # Scrape tabbed content
    tab_headers = soup.find_all("button", class_="tab-header")
    tab_contents = soup.find_all("div", class_="tab-content")

    for header, tab_content in zip(tab_headers, tab_contents):
        # Extract tab title
        title = header.get_text(strip=True) if header else "No Title"

        # Extract paragraphs (p)
        paragraphs = [p.get_text(strip=True) for p in tab_content.find_all("p")]

        # Extract lists (ul > li)
        lists = [li.get_text(strip=True) for li in tab_content.find_all("li")]

        # Extract links (a)
        links = [a.get_text(strip=True) + " - " + a["href"] for a in tab_content.find_all("a", href=True)]

        # Append the scraped data
        content.append({
            "url": url,
            "title": title,
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
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        logging.info(f"Scraping page: {url}")

        # Fetch the page content
        page_content = fetch_webpage(url)
        if not page_content:
            return

        # Parse the page HTML
        soup = BeautifulSoup(page_content, "html.parser")

        # Scrape the page using the appropriate function
        scraped_data = scrape_faculty_page(soup, url)

        # Open the output file to write the scraped data
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")

            # Write the scraped data to the file
            for data in scraped_data:
                write_to_txt(file, data)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()