import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
import argparse
from configparser import ConfigParser

# Import the logging configuration function
from logging_config import configure_logging

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
main_page_url = config.get('DEFAULT', 'phd_programs_url', fallback="https://jindal.utdallas.edu/phd-programs/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "phd_programs_data.txt")

# User-Agent header
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
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

def fetch_webpage(url, retries=3):
    """Fetch the webpage content with retries."""
    for attempt in range(retries):
        try:
            logging.info(f"Sending GET request to: {url}")
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                logging.info("Successfully retrieved the webpage.")
                return response.content
            else:
                logging.error(f"Failed to retrieve the webpage. Status code: {response.status_code}")
                logging.debug(f"Response content: {response.content}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                return None

def extract_menu_links(soup, base_url):
    """Extract links from the PhD menu."""
    menu_links = []
    menu_container = soup.find("div", class_="menu-phd-container")
    if menu_container:
        for link in menu_container.find_all("a", href=True):
            full_url = urljoin(base_url, link["href"])
            menu_links.append(full_url)
            logging.info(f"Found menu link: {full_url}")
    else:
        logging.warning("PhD menu container not found.")
    return menu_links

def extract_table_data(table):
    """Extract data from a table and return it as a list of rows."""
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.text.strip() for cell in row.find_all(["th", "td"])]
        rows.append(cells)
    return rows

def scrape_page(url, file):
    """Scrape headings, tables, paragraphs, lists, and specific classes from a page."""
    logging.info(f"Scraping page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n")

    # Extract headings (h1, h2, h3, h4)
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    if headings:
        file.write("\nHeadings:\n")
        for heading in headings:
            file.write(f"  {heading.text.strip()}\n")
            logging.debug(f"Processed heading: {heading.text.strip()}")

    # Extract tables
    tables = soup.find_all("table")
    if tables:
        file.write("\nTables:\n")
        for table in tables:
            rows = extract_table_data(table)
            for row in rows:
                file.write(f"  {', '.join(row)}\n")
            logging.debug(f"Processed table: {table.text.strip()}")

    # Extract paragraphs
    paragraphs = soup.find_all("p")
    if paragraphs:
        file.write("\nParagraphs:\n")
        for p in paragraphs:
            file.write(f"  {p.text.strip()}\n")
            logging.debug(f"Processed paragraph: {p.text.strip()}")

    # Extract lists (ul, ol)
    lists = soup.find_all(["ul", "ol"])
    if lists:
        file.write("\nLists:\n")
        for lst in lists:
            for li in lst.find_all("li"):
                file.write(f"  - {li.text.strip()}\n")
            logging.debug(f"Processed list: {lst.text.strip()}")

    # Extract specific classes (e.g., wideblock, smallblock, tab-content, stat-box)
    specific_classes = ["wideblock", "smallblock", "tab-content", "stat-box", "colgrid"]
    for class_name in specific_classes:
        elements = soup.find_all("div", class_=class_name)
        if elements:
            file.write(f"\nElements with class '{class_name}':\n")
            for element in elements:
                file.write(f"  {element.text.strip()}\n")
                logging.debug(f"Processed element with class '{class_name}': {element.text.strip()}")

    # Extract tabbed content (FAQ section)
    tab_headers = soup.find_all("button", class_="tab-header")
    if tab_headers:
        file.write("\nFAQ Section:\n")
        for tab in tab_headers:
            question = tab.text.strip()
            file.write(f"  Question: {question}\n")
            tab_content = tab.find_next("div", class_="tab-content")
            if tab_content:
                file.write(f"  Answer: {tab_content.text.strip()}\n")
            logging.debug(f"Processed FAQ: {question}")

    # Extract testimonials (if present)
    testimonials = soup.find_all("div", class_="post hentry ivycat-post colgrid")
    if testimonials:
        file.write("\nTestimonials:\n")
        for testimonial in testimonials:
            name = testimonial.find("h3", class_="sans")
            if name:
                file.write(f"  Name: {name.text.strip()}\n")
            quote = testimonial.find("blockquote")
            if quote:
                file.write(f"  Quote: {quote.text.strip()}\n")
            logging.debug(f"Processed testimonial: {name.text.strip() if name else 'No name'}")

    # Add a separator after the page content
    file.write("\n" + "=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Fetch the main page content
        main_page_content = fetch_webpage(main_page_url)
        if not main_page_content:
            return

        # Parse the main page HTML
        main_soup = BeautifulSoup(main_page_content, "html.parser")

        # Extract links from the PhD menu
        menu_links = extract_menu_links(main_soup, main_page_url)

        # Open the output file to write the scraped data with UTF-8 encoding
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")

            # Scrape each linked page
            for link in menu_links:
                scrape_page(link, file)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()