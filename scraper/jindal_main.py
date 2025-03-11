import os
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

# URL of the website to scrape
url = config.get('DEFAULT', 'URL', fallback="https://jindal.utdallas.edu/")

# Directory and file path
output_dir = config.get('DEFAULT', 'OUTPUT_DIR', fallback="../scraped_data")
output_file = os.path.join(output_dir, "jindal_main_site.txt")

# User-Agent header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}


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


def scrape_headings(soup, file):
    """Scrape content under <h2> and <h3> headings, avoiding redundancy."""
    logging.info("Scraping headings and subheadings.")
    h2_headings = soup.find_all('h2')
    logging.info(f"Found {len(h2_headings)} <h2> headings.")

    # Set to keep track of already scraped headings
    scraped_headings = set()

    for heading in h2_headings:
        heading_text = heading.text.strip()

        if heading_text.lower() == "upcoming events":
            logging.debug(f"Skipping 'Upcoming Events' heading: {heading_text}")
            continue

        # Skip if the heading has already been scraped
        if heading_text in scraped_headings:
            logging.debug(f"Skipping already scraped heading: {heading_text}")
            continue

        # Add the heading to the set of scraped headings
        scraped_headings.add(heading_text)
        file.write(f"Heading (h2): {heading_text}\n")
        logging.info(f"Processing <h2> heading: {heading_text}")

        # Find the next sibling elements until the next <h2> heading
        next_element = heading.find_next_sibling()
        while next_element and next_element.name != 'h2':
            # If the next element is an <h3>, handle it
            if next_element.name == 'h3':
                h3_text = next_element.text.strip()

                # Skip if the <h3> subheading has already been scraped
                if h3_text in scraped_headings:
                    logging.debug(f"Skipping already scraped subheading: {h3_text}")
                    next_element = next_element.find_next_sibling()
                    continue

                # Add the <h3> subheading to the set of scraped headings
                scraped_headings.add(h3_text)
                file.write(f"\tSubheading (h3): {h3_text}\n")
                logging.info(f"Processing <h3> subheading: {h3_text}")

                # Find content under the <h3> heading
                h3_next_element = next_element.find_next_sibling()
                while h3_next_element and h3_next_element.name not in ['h2', 'h3']:
                    # Write content under <h3> (e.g., paragraphs, lists, etc.)
                    if h3_next_element.name in ['p', 'ul', 'ol', 'div']:
                        file.write(f"\t\t{h3_next_element.text.strip()}\n")
                        logging.debug(f"Processed content under <h3>: {h3_next_element.text.strip()}")
                    h3_next_element = h3_next_element.find_next_sibling()

            # If the next element is a <p>, <ul>, <ol>, or <div>, write it under the <h2>
            elif next_element.name in ['p', 'ul', 'ol', 'div']:
                file.write(f"\t{next_element.text.strip()}\n")
                logging.debug(f"Processed content under <h2>: {next_element.text.strip()}")

            # Move to the next sibling element
            next_element = next_element.find_next_sibling()

        # Add a separator between sections
        file.write("\n" + "=" * 50 + "\n\n")

def scrape_lists_and_links(soup, file):
    """Scrape <li> and <a> tags and associate them with their parent or sibling elements."""
    logging.info("Scraping <li> and <a> tags with context.")

    # Scrape <li> tags within <ul> or <ol>
    lists = soup.find_all(['ul', 'ol'])
    if lists:
        file.write("Lists and List Items:\n")
        for list_element in lists:
            # Find the parent heading or paragraph for context
            context = list_element.find_previous(['h2', 'h3', 'p'])
            context_text = context.text.strip() if context else "No Context"

            file.write(f"\nContext: {context_text}\n")
            logging.debug(f"Processing list under context: {context_text}")

            list_items = list_element.find_all('li')
            for item in list_items:
                item_text = item.text.strip()
                if item_text:
                    file.write(f"\t- {item_text}\n")
                    logging.debug(f"Processed list item: {item_text}")
        file.write("\n" + "=" * 50 + "\n\n")

    # Scrape <a> tags and associate them with their parent or sibling elements
    links = soup.find_all('a', href=True)
    if links:
        file.write("Links and Their Context:\n")
        for link in links:
            link_text = link.text.strip()
            link_href = link['href']

            # Find the parent or previous sibling for context
            context = link.find_previous(['h2', 'h3', 'p', 'li'])
            context_text = context.text.strip() if context else "No Context"

            if link_text or link_href:
                file.write(f"\nContext: {context_text}\n")
                file.write(f"\t- Text: {link_text}\n")
                file.write(f"\t  Href: {link_href}\n")
                logging.debug(f"Processed link: {link_text} -> {link_href} under context: {context_text}")
        file.write("\n" + "=" * 50 + "\n\n")


def scrape_at_a_glance(soup, file):
    """Scrape the 'At a Glance' section."""
    logging.info("Scraping 'At a Glance' section.")
    glance_section = soup.find('h3', text='At a Glance')
    if glance_section:
        logging.info("Found 'At a Glance' section.")
        file.write("At a Glance:\n")

        glance_container = glance_section.find_next('div', class_='glance__container')
        if glance_container:
            for item in glance_container.find_all('div'):
                number = item.find('p', class_='glance__number')
                title = item.find('p', class_='glance__title')
                description = item.find('p', class_='glance__description')

                if number and title and description:
                    file.write(f"\t{number.text.strip()} {title.text.strip()}\n")
                    file.write(f"\t\t{description.text.strip()}\n")
                    logging.debug(f"Processed item: {number.text.strip()} {title.text.strip()}")

            logging.info("Processed 'At a Glance' section.")
        else:
            logging.warning("No 'glance__container' found in 'At a Glance' section.")
    else:
        logging.warning("No 'At a Glance' section found.")

    # Add a separator after the section
    file.write("\n" + "=" * 50 + "\n\n")



def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Fetch the webpage content
    webpage_content = fetch_webpage(url)
    if not webpage_content:
        return

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(webpage_content, 'html.parser')

    # Open the text file to write the scraped data
    with open(output_file, 'w', encoding='utf-8') as file:
        logging.info(f"Opened file for writing: {output_file}")


        # Scrape 'At a Glance' section
        scrape_at_a_glance(soup, file)


     # Scrape headings and subheadings
        scrape_headings(soup, file)

        # Scrape <li> and <a> tags
        scrape_lists_and_links(soup, file)
    logging.info(f"Data scraped successfully and saved to '{output_file}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Scraper for Jindal School of Management")
    parser.add_argument('--url', type=str, default=url, help="URL of the website to scrape")
    args = parser.parse_args()

    url = args.url
    main()