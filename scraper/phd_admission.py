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

# URL of the new page to scrape
new_page_url = config.get('DEFAULT', 'phd_admissions_url', fallback="https://jindal.utdallas.edu/phd-programs/admission-requirements/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'output_dir', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "phd_admissions.txt")

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

def scrape_new_page(url, file):
    """Scrape the required sections from the new page."""
    logging.info(f"Scraping new page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n")

    # Extract the hero box (Fall 2026 Applications)
    hero_box = soup.find("div", class_="hero-box green")
    if hero_box:
        display_text = hero_box.find("p", class_="display")
        if display_text:
            file.write(f"\nHero Box: {display_text.text.strip()}\n")
            logging.info(f"Processed hero box: {display_text.text.strip()}")
    else:
        logging.warning("Hero box not found.")

    # Extract the "Required Application Materials" section
    app_materials_section = soup.find("div", class_="wideblock overflow")
    if app_materials_section:
        file.write("\nSection: Required Application Materials\n")
        heading = app_materials_section.find("h2")
        if heading:
            file.write(f"  Heading: {heading.text.strip()}\n")
            logging.info(f"Processed heading: {heading.text.strip()}")

        # Extract the <ul> list
        ul = app_materials_section.find("ul")
        if ul:
            file.write("  List:\n")
            for li in ul.find_all("li"):
                file.write(f"    - {li.text.strip()}\n")
                logging.debug(f"Processed list item: {li.text.strip()}")

        # Extract <p> elements
        for p in app_materials_section.find_all("p"):
            file.write(f"  Paragraph: {p.text.strip()}\n")
            logging.debug(f"Processed paragraph: {p.text.strip()}")
    else:
        logging.warning("Required Application Materials section not found.")

    # Extract the "PhD Admissions Overview" section
    phd_overview_section = soup.find("div", id="program-overview")
    if phd_overview_section:
        file.write("\nSection: PhD Admissions Overview\n")
        heading = phd_overview_section.find("h2")
        if heading:
            file.write(f"  Heading: {heading.text.strip()}\n")
            logging.info(f"Processed heading: {heading.text.strip()}")

        # Extract <p> elements
        for p in phd_overview_section.find_all("p"):
            file.write(f"  Paragraph: {p.text.strip()}\n")
            logging.debug(f"Processed paragraph: {p.text.strip()}")
    else:
        logging.warning("PhD Admissions Overview section not found.")

    # Extract the "Student Funding" section
    funding_section = soup.find("div", class_="smallblock green overflow")
    if funding_section:
        file.write("\nSection: Student Funding\n")
        heading = funding_section.find("h2")
        if heading:
            file.write(f"  Heading: {heading.text.strip()}\n")
            logging.info(f"Processed heading: {heading.text.strip()}")

        # Extract <p> elements
        for p in funding_section.find_all("p"):
            file.write(f"  Paragraph: {p.text.strip()}\n")
            logging.debug(f"Processed paragraph: {p.text.strip()}")
    else:
        logging.warning("Student Funding section not found.")

    # Add a separator after the page content
    file.write("\n" + "=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Open the output file to write the scraped data with UTF-8 encoding
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")

            # Scrape the new page
            scrape_new_page(new_page_url, file)

        logging.info(f"Data scraped successfully and saved to '{output_file}'")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()