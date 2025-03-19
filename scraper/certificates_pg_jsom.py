import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the main page to scrape
main_page_url = "https://jindal.utdallas.edu/certificate-programs/"

# Output directory and file
output_dir = "../scraped_data"
output_file = os.path.join(output_dir, "certificate_programs_data.txt")

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

def extract_menu_links(soup, base_url):
    """Extract links from the certificates menu."""
    menu_links = []
    menu_container = soup.find("div", class_="menu-certificates-container")
    if menu_container:
        for link in menu_container.find_all("a", href=True):
            full_url = urljoin(base_url, link["href"])
            menu_links.append(full_url)
            logging.info(f"Found menu link: {full_url}")
    else:
        logging.warning("Certificates menu container not found.")
    return menu_links

def extract_tabbed_content(soup):
    """Extract content from tabbed sections."""
    tabs = soup.find_all("div", class_="tabs")
    data = []
    for tab in tabs:
        tab_data = {}
        headers = tab.find_all("button", class_="tab-header")
        for header in headers:
            key = header.text.strip()
            content = []
            tab_content = header.find_next("div", class_="tab-content")
            if tab_content:
                paragraphs = tab_content.find_all("p")
                for p in paragraphs:
                    content.append(f"Paragraph: {p.text.strip()}")
                lists = tab_content.find_all("ul")
                for lst in lists:
                    items = [f"  - {li.text.strip()} (Link: {li.a['href']})" if li.a else f"  - {li.text.strip()}" for li in lst.find_all("li")]
                    content.append("List:\n" + "\n".join(items))
            tab_data[key] = content
        data.append(tab_data)
    return data

def extract_wideblock_content(soup):
    """Extract content from wideblock sections."""
    wideblocks = soup.find_all("div", class_="wideblock")
    data = []
    for block in wideblocks:
        block_data = {}
        headings = block.find_all(["h2", "h3"])
        for heading in headings:
            key = heading.text.strip()
            content = []
            next_element = heading.find_next_sibling()
            while next_element and next_element.name not in ["h2", "h3"]:
                if next_element.name == "p":
                    content.append(f"Paragraph: {next_element.text.strip()}")
                elif next_element.name == "ul":
                    items = [f"  - {li.text.strip()} (Link: {li.a['href']})" if li.a else f"  - {li.text.strip()}" for li in next_element.find_all("li")]
                    content.append("List:\n" + "\n".join(items))
                elif next_element.name == "a" and next_element.get("href"):
                    content.append(f"Link: {next_element.text.strip()} (URL: {next_element['href']})")
                next_element = next_element.find_next_sibling()
            block_data[key] = content
        data.append(block_data)
    return data

def extract_smallblock_content(soup):
    """Extract content from smallblock sections."""
    smallblocks = soup.find_all("div", class_="smallblock")
    data = []
    for block in smallblocks:
        block_data = {}
        headings = block.find_all(["h2", "h3"])
        for heading in headings:
            key = heading.text.strip()
            content = []
            next_element = heading.find_next_sibling()
            while next_element and next_element.name not in ["h2", "h3"]:
                if next_element.name == "p":
                    content.append(f"Paragraph: {next_element.text.strip()}")
                elif next_element.name == "ul":
                    items = [f"  - {li.text.strip()} (Link: {li.a['href']})" if li.a else f"  - {li.text.strip()}" for li in next_element.find_all("li")]
                    content.append("List:\n" + "\n".join(items))
                elif next_element.name == "a" and next_element.get("href"):
                    content.append(f"Link: {next_element.text.strip()} (URL: {next_element['href']})")
                next_element = next_element.find_next_sibling()
            block_data[key] = content
        data.append(block_data)
    return data

def scrape_page(url, file):
    """Scrape content from a page and write it to the file."""
    logging.info(f"Scraping page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n\n")

    # Extract and write wideblock content
    wideblocks = extract_wideblock_content(soup)
    if wideblocks:
        file.write("Wideblocks:\n")
        for block in wideblocks:
            for heading, content in block.items():
                file.write(f"{heading}:\n")
                for item in content:
                    file.write(f"{item}\n")
                file.write("\n")

    # Extract and write smallblock content
    smallblocks = extract_smallblock_content(soup)
    if smallblocks:
        file.write("Smallblocks:\n")
        for block in smallblocks:
            for heading, content in block.items():
                file.write(f"{heading}:\n")
                for item in content:
                    file.write(f"{item}\n")
                file.write("\n")

    # Extract and write tabbed content
    tabs = extract_tabbed_content(soup)
    if tabs:
        file.write("Tabs:\n")
        for tab in tabs:
            for header, content in tab.items():
                file.write(f"{header}:\n")
                for item in content:
                    file.write(f"{item}\n")
                file.write("\n")

    # Add a separator after the page content
    file.write("=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Fetch the main page content
    main_page_content = fetch_webpage(main_page_url)
    if not main_page_content:
        return

    # Parse the main page HTML
    main_soup = BeautifulSoup(main_page_content, "html.parser")

    # Extract links from the certificates menu
    menu_links = extract_menu_links(main_soup, main_page_url)

    # Open the output file to write the scraped data
    with open(output_file, "w", encoding="utf-8") as file:
        logging.info(f"Opened file for writing: {output_file}")

        # Scrape the main page
        scrape_page(main_page_url, file)

        # Scrape each linked page
        for link in menu_links:
            scrape_page(link, file)

    logging.info(f"Data scraped successfully and saved to '{output_file}'")

if __name__ == "__main__":
    main()