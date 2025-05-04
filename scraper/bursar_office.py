import os
from urllib.parse import urljoin
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser

# Configure logging to only display to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load configuration
config = ConfigParser()
config.read('config.ini')

# URL of the page to scrape
page_url = "https://bursar.utdallas.edu/"

# Output directories - local and git
local_output_dir = "../scraped_data"  # For local use
git_output_dir = "scraped_data_git"  # For GitHub Actions

# Determine which output directory to use based on environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'
output_dir = git_output_dir if is_github_env else local_output_dir

# Log environment information
logging.info(f"Running in {'GitHub Actions' if is_github_env else 'local'} environment")
logging.info(f"Using output directory: {output_dir}")

# Output file path
output_file = os.path.join(output_dir, "bursar_data.txt")

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
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                return None


def extract_content(soup):
    """Extract content from the page and return it as a structured string."""
    content = []

    # Extract main content within <div role="main">
    main_content = soup.find("div", role="main")
    if main_content:
        # Extract paragraphs
        paragraphs = main_content.find_all("p")
        for p in paragraphs:
            paragraph_text = p.text.strip()
            links = [f"{a.text.strip()} (URL: {a['href']})" for a in p.find_all("a", href=True)]
            if links:
                content.append(f"Paragraph: {paragraph_text}\n  Links: {', '.join(links)}")
            else:
                content.append(f"Paragraph: {paragraph_text}")

        # Extract lists
        lists = main_content.find_all("ul")
        for lst in lists:
            items = [f"  - {li.text.strip()} (URL: {li.a['href']})" if li.a else f"  - {li.text.strip()}" for li in
                     lst.find_all("li")]
            content.append("List:\n" + "\n".join(items))

        # Extract tables
        tables = main_content.find_all("table")
        for table in tables:
            rows = []
            for row in table.find_all("tr"):
                cells = [cell.text.strip() for cell in row.find_all(["th", "td"])]
                rows.append(" | ".join(cells))
            content.append("Table:\n" + "\n".join(rows))

        # Extract headings and associated content
        headings = main_content.find_all(["h2", "h3"])
        for heading in headings:
            heading_text = heading.text.strip()
            content.append(f"Heading: {heading_text}")
            next_element = heading.find_next_sibling()
            while next_element and next_element.name not in ["h2", "h3"]:
                if next_element.name == "p":
                    paragraph_text = next_element.text.strip()
                    links = [f"{a.text.strip()} (URL: {a['href']})" for a in next_element.find_all("a", href=True)]
                    if links:
                        content.append(f"  Paragraph: {paragraph_text}\n    Links: {', '.join(links)}")
                    else:
                        content.append(f"  Paragraph: {paragraph_text}")
                elif next_element.name == "ul":
                    items = [f"    - {li.text.strip()} (URL: {li.a['href']})" if li.a else f"    - {li.text.strip()}"
                             for li in next_element.find_all("li")]
                    content.append("  List:\n" + "\n".join(items))
                elif next_element.name == "table":
                    rows = []
                    for row in next_element.find_all("tr"):
                        cells = [cell.text.strip() for cell in row.find_all(["th", "td"])]
                        rows.append(" | ".join(cells))
                    content.append("  Table:\n" + "\n".join(rows))
                next_element = next_element.find_next_sibling()

    return "\n".join(content)


def scrape_page(url):
    """Scrape content from a page and return it as a string."""
    logging.info(f"Scraping page: {url}")
    content = fetch_webpage(url)
    if not content:
        return None

    soup = BeautifulSoup(content, "html.parser")
    return extract_content(soup)


def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Scrape the page
    page_content = scrape_page(page_url)
    if not page_content:
        return

    # Save the scraped data to a text file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(f"URL: {page_url}\n\n")
        file.write(page_content)
    logging.info(f"Data scraped successfully and saved to '{output_file}'")

    print(f"URL: {page_url}\n")


if __name__ == "__main__":
    main()