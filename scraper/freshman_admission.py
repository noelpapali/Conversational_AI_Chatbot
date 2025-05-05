import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
import argparse
from configparser import ConfigParser

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Determine environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the main page to scrape
main_url = config.get('DEFAULT', 'main_url', fallback="https://enroll.utdallas.edu/freshman/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "freshman_admission.txt")

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

def extract_h3_links(soup, base_url):
    """Extract links from <h3> tags."""
    h3_links = []
    h3_tags = soup.find_all("h3")
    for h3 in h3_tags:
        link = h3.find("a", href=True)
        if link:
            full_url = urljoin(base_url, link["href"])
            h3_links.append(full_url)
            logging.info(f"Found link in <h3>: {full_url}")
    return h3_links

def extract_table_data(table):
    """Extract data from a table and return it as a list of rows."""
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.text.strip() for cell in row.find_all(["th", "td"])]
        rows.append(cells)
    return rows

def scrape_linked_page(url, file):
    """Scrape <p>, <ul>, and specific div classes under <h1> and <h3> headings."""
    logging.info(f"Scraping linked page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n")

    # Find all <h1> and <h3> headings
    headings = soup.find_all(["h1", "h3"])

    for heading in headings:
        heading_text = heading.text.strip()
        file.write(f"\nHeading: {heading_text}\n")
        logging.info(f"Processing heading: {heading_text}")

        # Find the next sibling elements after the heading
        next_element = heading.find_next_sibling()
        while next_element and next_element.name not in ["h1", "h2", "h3"]:
            if next_element.name == "p":
                file.write(f"  Paragraph: {next_element.text.strip()}\n")
                logging.debug(f"Processed paragraph under {heading_text}: {next_element.text.strip()}")
            elif next_element.name == "ul":
                file.write("  List:\n")
                for li in next_element.find_all("li"):
                    file.write(f"    - {li.text.strip()}\n")
                    logging.debug(f"Processed list item under {heading_text}: {li.text.strip()}")
            elif next_element.name == "div":
                # Check for the specific div class
                div_class = next_element.get("class", [])
                if "wp-block-column" in div_class and "is-layout-flow" in div_class:
                    file.write("  Div Content:\n")
                    for div_content in next_element.find_all(["p", "ul", "h3"]):
                        if div_content.name == "p":
                            file.write(f"    Paragraph: {div_content.text.strip()}\n")
                        elif div_content.name == "ul":
                            file.write("    List:\n")
                            for li in div_content.find_all("li"):
                                file.write(f"      - {li.text.strip()}\n")
                        elif div_content.name == "h3":
                            file.write(f"    Subheading: {div_content.text.strip()}\n")
                    logging.debug(f"Processed div content under {heading_text}")
            elif next_element.name == "figure":
                # Check for tables with specific classes
                figure_class = next_element.get("class", [])
                if "wp-block-table" in figure_class:
                    if "is-style-regular" in figure_class:
                        file.write("  Table (Regular Style):\n")
                        table = next_element.find("table")
                        if table:
                            rows = extract_table_data(table)
                            for row in rows:
                                file.write(f"    {', '.join(row)}\n")
                            logging.debug(f"Processed regular table under {heading_text}")
                    elif "is-style-stripes" in figure_class:
                        file.write("  Table (Stripes Style):\n")
                        table = next_element.find("table")
                        if table:
                            rows = extract_table_data(table)
                            for row in rows:
                                file.write(f"    {', '.join(row)}\n")
                            logging.debug(f"Processed striped table under {heading_text}")
            next_element = next_element.find_next_sibling()

        # Add a separator after each heading section
        file.write("\n" + "-" * 50 + "\n")

    # Add a separator between pages
    file.write("\n" + "=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Fetch the main page content
        main_page_content = fetch_webpage(main_url)
        if not main_page_content:
            return

        # Parse the main page HTML
        main_soup = BeautifulSoup(main_page_content, "html.parser")

        # Extract links from <h3> tags
        h3_links = extract_h3_links(main_soup, main_url)

        # Open the output file to write the scraped data with UTF-8 encoding
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")

            # Scrape each linked page
            for link in h3_links:
                scrape_linked_page(link, file)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()