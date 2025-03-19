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

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the new page to scrape
new_page_url = "https://jindal.utdallas.edu/admission-requirements/masters/"

# Output directory and file
output_dir = "../scraped_data"
output_file = os.path.join(output_dir, "masters_admission.txt")

# User-Agent header
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

def create_output_directory():
    """Create the output directory if it doesn't exist."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

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

def extract_table_data(table):
    """Extract data from a table and return it as a list of rows."""
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.text.strip() for cell in row.find_all(["th", "td"])]
        rows.append(cells)
    return rows

def scrape_tabbed_content(tabbed_content, file):
    """Scrape content from tabbed sections."""
    for tab in tabbed_content.find_all("button", class_="tab-header"):
        heading = tab.find("h2")
        if heading:
            heading_text = heading.text.strip()
            file.write(f"\nHeading: {heading_text}\n")
            logging.info(f"Processing tab heading: {heading_text}")

            # Find the corresponding tab content
            tab_content = tab.find_next("div", class_="tab-content")
            if tab_content:
                for content in tab_content.find_all(["p", "ul"]):
                    if content.name == "p":
                        file.write(f"  Paragraph: {content.text.strip()}\n")
                        logging.debug(f"Processed paragraph under {heading_text}: {content.text.strip()}")
                    elif content.name == "ul":
                        file.write("  List:\n")
                        for li in content.find_all("li"):
                            file.write(f"    - {li.text.strip()}\n")
                            logging.debug(f"Processed list item under {heading_text}: {li.text.strip()}")
                file.write("\n" + "-" * 50 + "\n")

def scrape_new_page(url, file):
    """Scrape the table, <p> elements within entry-content, and tabbed content."""
    logging.info(f"Scraping new page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n")

    # Find the table with the caption "Master’s Application Deadlines"
    table = soup.find("caption", text="Master’s Application Deadlines").find_parent("table")
    if table:
        file.write("\nTable: Master’s Application Deadlines\n")
        rows = extract_table_data(table)
        for row in rows:
            file.write(f"  {', '.join(row)}\n")
        logging.info("Processed table: Master’s Application Deadlines")
    else:
        logging.warning("Table with caption 'Master’s Application Deadlines' not found.")

    # Find the <div> with class "entry-content" and extract <p> elements
    entry_content = soup.find("div", class_="entry-content")
    if entry_content:
        file.write("\nParagraphs in entry-content:\n")
        for p in entry_content.find_all("p"):
            file.write(f"  {p.text.strip()}\n")
            logging.debug(f"Processed paragraph: {p.text.strip()}")
    else:
        logging.warning("Div with class 'entry-content' not found.")

    # Scrape tabbed content from the "Application Requirements" section
    app_req_section = soup.find("div", class_="wideblock warm-gray-0 overflow")
    if app_req_section:
        file.write("\nSection: Application Requirements\n")
        tabbed_content = app_req_section.find("div", class_="tabs tab-accordion")
        if tabbed_content:
            scrape_tabbed_content(tabbed_content, file)
        else:
            logging.warning("Tabbed content not found in Application Requirements section.")

    # Scrape tabbed content from the "Additional Considerations" section
    add_cons_section = soup.find("div", class_="wideblock warm-gray-1 overflow")
    if add_cons_section:
        file.write("\nSection: Additional Considerations\n")
        tabbed_content = add_cons_section.find("div", class_="tabs tab-accordion")
        if tabbed_content:
            scrape_tabbed_content(tabbed_content, file)
        else:
            logging.warning("Tabbed content not found in Additional Considerations section.")

    # Add a separator after the page content
    file.write("\n" + "=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Open the output file to write the scraped data with UTF-8 encoding
    with open(output_file, "w", encoding="utf-8") as file:
        logging.info(f"Opened file for writing: {output_file}")

        # Scrape the new page
        scrape_new_page(new_page_url, file)

    logging.info(f"Data scraped successfully and saved to '{output_file}'")

if __name__ == "__main__":
    main()
