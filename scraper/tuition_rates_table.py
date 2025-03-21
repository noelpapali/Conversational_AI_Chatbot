import os
import requests
import logging
from bs4 import BeautifulSoup
import argparse
from configparser import ConfigParser
import csv

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the website to scrape
url = config.get('DEFAULT', 'URL', fallback="https://bursar.utdallas.edu/tuition/tuition-plans-rates/")

# Directory and file paths
output_dir = config.get('DEFAULT', 'OUTPUT_DIR', fallback="../scraped_data")
csv_output_file = os.path.join(output_dir, "tuition_rates_table.csv")

# User-Agent header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
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



def extract_tables(soup):
    """Extract all tables from the webpage and save them to a CSV file."""
    logging.info("Extracting tables.")
    tables_data = []

    for table in soup.find_all('table'):
        table_data = []
        rows = table.find_all('tr')

        # Extract headers
        headers = [header.text.strip() for header in rows[0].find_all('th')]
        table_data.append(headers)

        # Extract rows
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.text.strip() for cell in cells]
            table_data.append(row_data)

        tables_data.append(table_data)

    return tables_data


def save_tables_to_csv(tables_data, file_path):
    """Save the extracted tables to a CSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        for table in tables_data:
            writer.writerows(table)
            writer.writerow([])  # Add an empty row between tables for separation

    logging.info(f"Tables saved to '{file_path}'.")


def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Fetch the webpage content
    webpage_content = fetch_webpage(url)
    if not webpage_content:
        return

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(webpage_content, 'html.parser')

    # Extract tables
    tables_data = extract_tables(soup)
    save_tables_to_csv(tables_data, csv_output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Scraper for Tuition Plans and Rates")
    parser.add_argument('--url', type=str, default=url, help="URL of the website to scrape")
    args = parser.parse_args()

    url = args.url
    main()