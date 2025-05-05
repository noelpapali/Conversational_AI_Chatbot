import os
import requests
import logging
from bs4 import BeautifulSoup
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

# URL of the website to scrape
url = config.get('DEFAULT', 'URL', fallback="https://jindal.utdallas.edu/calendar/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'OUTPUT_DIR', fallback="../scraped_data")
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "events.txt")

# User-Agent header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
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

def scrape_events(soup, file):
    """Scrape event data from the webpage."""
    logging.info("Scraping event data.")

    # Find all <h2> elements (months and years)
    h2_elements = soup.find_all('h2')
    if not h2_elements:
        logging.warning("No <h2> elements found.")
        return

    for h2 in h2_elements:
        month_year = h2.text.strip()
        file.write(f"Month: {month_year}\n\n")
        logging.info(f"Processing events for: {month_year}")

        # Find all event containers within the same section as the <h2>
        next_element = h2.find_next_sibling()
        while next_element and next_element.name != 'h2':
            if next_element.name == 'div' and 'event-line' in next_element.get('class', []):
                # Extract event date
                event_date = next_element.find('span', class_='event-date')
                date = event_date.text.strip() if event_date else "No Date"

                # Extract event time
                event_time = next_element.find('span', class_='event-time')
                time = event_time.text.strip() if event_time else "No Time"

                # Extract event title
                event_title = next_element.find('h3', class_='event-title')
                title = event_title.text.strip() if event_title else "No Title"

                # Extract event location
                event_location = next_element.find('div', class_='event-location')
                location = event_location.text.strip() if event_location else "No Location"

                # Extract event URL from <a> tag
                event_link = next_element.find('a', href=True)
                event_url = event_link['href'] if event_link else "No URL"

                # Write event details to the file
                file.write(f"Date: {date}\n")
                file.write(f"Time: {time}\n")
                file.write(f"Title: {title}\n")
                file.write(f"Location: {location}\n")
                file.write(f"Event URL: {event_url}\n")
                file.write("-" * 50 + "\n")
                logging.debug(f"Processed event: {title} on {date} at {time} in {location} -> {event_url}")

            next_element = next_element.find_next_sibling()

    logging.info("Event data scraped successfully.")

def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Fetch the webpage content
        webpage_content = fetch_webpage(url)
        if not webpage_content:
            return

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(webpage_content, 'html.parser')

        # Open the text file to write the scraped data
        with open(output_file, 'w', encoding='utf-8') as file:
            logging.info(f"Writing output to: {output_file}")

            # Scrape event data
            scrape_events(soup, file)

        logging.info(f"Event data scraped successfully and saved to '{output_file}'")
    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

if __name__ == "__main__":
    main()