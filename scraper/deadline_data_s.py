import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from urllib.parse import urljoin
import logging
from configparser import ConfigParser

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

# Configuration
base_url = config.get('DEFAULT', 'base_url', fallback="https://finaid.utdallas.edu")
deadlines_url = urljoin(base_url, "deadlines/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'tables', fallback="../tables")
git_output_dir = "tables_git"
output_folder = git_output_dir if is_github_env else local_output_dir

def fetch_webpage(url):
    """Fetch the webpage content with error handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching webpage: {e}")
        return None

def parse_html(content):
    """Parse the HTML content using BeautifulSoup."""
    return BeautifulSoup(content, 'html.parser')

def clean_filename(text):
    """Clean text to create valid filenames."""
    text = re.sub(r'[^\w\s-]', '', text).strip()
    return re.sub(r'[-\s]+', '_', text).lower()

def extract_tables_with_headings(soup):
    """Extract tables along with their headings from the page."""
    tables_data = []

    # Find all table containers (wp-block-columns)
    table_containers = soup.find_all('div', class_='wp-block-columns')
    logging.info(f"Found {len(table_containers)} table containers")

    for container in table_containers:
        # Find all columns within the container
        columns = container.find_all('div', class_='wp-block-column')

        for column in columns:
            # Extract the heading (h3) for the table
            heading = column.find('h3', class_='wp-block-heading')
            heading_text = heading.get_text(strip=True) if heading else "Unknown_Deadline"

            # Find the table within this column
            table = column.find('figure', class_='wp-block-table')
            if table:
                table_element = table.find('table')
                if table_element:
                    tables_data.append({
                        'heading': heading_text,
                        'table': table_element
                    })
                    logging.debug(f"Found table with heading: {heading_text}")

    logging.info(f"Extracted {len(tables_data)} tables with headings")
    return tables_data

def process_table(table_element):
    """Process a table element and return data as a DataFrame."""
    # Extract headers
    headers = [th.get_text(strip=True) for th in table_element.find_all('th')]

    # Extract rows
    rows = []
    for tr in table_element.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if cells:
            rows.append(cells)

    # Create DataFrame (skip header row if it exists in the data)
    if len(rows) > 1 and rows[0] == headers:
        return pd.DataFrame(rows[1:], columns=headers)
    return pd.DataFrame(rows, columns=headers)

def save_tables_to_csv(tables_data, output_folder):
    """Save extracted tables to CSV files."""
    try:
        os.makedirs(output_folder, exist_ok=True)
        logging.info(f"Created output directory: {output_folder}")

        for i, table_info in enumerate(tables_data, start=1):
            try:
                df = process_table(table_info['table'])
                if not df.empty:
                    filename = f"{clean_filename(table_info['heading'])}_{i}.csv"
                    filepath = os.path.join(output_folder, filename)
                    df.to_csv(filepath, index=False)
                    logging.info(f"Saved: {filename}")
                else:
                    logging.warning(f"Skipped empty table: {table_info['heading']}")
            except Exception as e:
                logging.error(f"Error processing table {i}: {e}")
    except Exception as e:
        logging.error(f"Failed to create output directory {output_folder}: {e}")
        raise

def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")

        # Fetch and parse the webpage
        content = fetch_webpage(deadlines_url)
        if not content:
            return

        soup = parse_html(content)

        # Extract tables with their headings
        tables_data = extract_tables_with_headings(soup)

        if not tables_data:
            logging.warning("No tables found on the page.")
            return

        # Save tables to CSV files
        save_tables_to_csv(tables_data, output_folder)
        logging.info(f"Successfully extracted {len(tables_data)} tables to '{output_folder}' directory.")

    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()