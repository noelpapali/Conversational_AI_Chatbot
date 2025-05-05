import os
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser
import time

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

# URL of the page to scrape
page_url = config.get('DEFAULT', 'page_url', fallback="https://jindal.utdallas.edu/centers-of-excellence/")

# Output directories - local and git
local_output_dir = config.get('DEFAULT', 'scraped_data', fallback="../scraped_data")
git_output_dir = os.path.join("chatbot", "scraped_data_git")
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "centers_of_excellence_data.txt")

# Rate limiting delay
REQUEST_DELAY = int(config.get('DEFAULT', 'request_delay', fallback=2))

# User-Agent header to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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

def fetch_webpage(url):
    """Fetch the content of a webpage with error handling."""
    try:
        logging.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def scrape_main_heading(soup, url):
    """Scrape the main heading from the page - EXACTLY AS IN YOUR ORIGINAL CODE"""
    try:
        main_heading = soup.find("div", class_="entry-title")
        if main_heading:
            return {
                "url": url,
                "title": main_heading.get_text(strip=True),
                "content": [],
                "lists": [],
                "links": []
            }
        return None
    except Exception as e:
        logging.error(f"Error scraping main heading: {e}")
        return None

def scrape_wideblock_content(soup, url):
    """Scrape content from wideblock overflow divs - EXACTLY AS IN YOUR ORIGINAL CODE"""
    try:
        content = []
        wideblocks = soup.find_all("div", class_="wideblock overflow")

        for block in wideblocks:
            headings = [h.get_text(strip=True) for h in block.find_all(["h2", "h3", "h4"])]
            paragraphs = [p.get_text(strip=True) for p in block.find_all("p")]
            lists = [li.get_text(strip=True) for li in block.find_all("li")]
            links = [f"{a.get_text(strip=True)} - {a['href']}" for a in block.find_all("a", href=True)]

            content.append({
                "url": url,
                "headings": headings,
                "content": paragraphs,
                "lists": lists,
                "links": links
            })

        return content
    except Exception as e:
        logging.error(f"Error scraping wideblock content: {e}")
        return []

def scrape_stat_boxes(soup, url):
    """Scrape content from stat-box divs - EXACTLY AS IN YOUR ORIGINAL CODE"""
    try:
        content = []
        stat_boxes = soup.find_all("div", class_="stat-box")

        for box in stat_boxes:
            headings = [h.get_text(strip=True) for h in box.find_all(["h2", "h3", "h4"])]
            paragraphs = [p.get_text(strip=True) for p in box.find_all("p")]
            lists = [li.get_text(strip=True) for li in box.find_all("li")]
            links = [f"{a.get_text(strip=True)} - {a['href']}" for a in box.find_all("a", href=True)]

            content.append({
                "url": url,
                "headings": headings,
                "content": paragraphs,
                "lists": lists,
                "links": links
            })

        return content
    except Exception as e:
        logging.error(f"Error scraping stat boxes: {e}")
        return []

def write_to_txt(file, data):
    """Write scraped data to a text file - EXACTLY AS IN YOUR ORIGINAL CODE"""
    try:
        file.write(f"URL: {data['url']}\n")
        if "title" in data:
            file.write(f"Title: {data['title']}\n")
        if data.get('headings'):
            file.write("Headings:\n")
            for heading in data['headings']:
                file.write(f"- {heading}\n")
        if data.get('content'):
            file.write("Content:\n")
            for paragraph in data['content']:
                file.write(f"{paragraph}\n")
        if data.get('lists'):
            file.write("Lists:\n")
            for item in data['lists']:
                file.write(f"- {item}\n")
        if data.get('links'):
            file.write("Links:\n")
            for link in data['links']:
                file.write(f"- {link}\n")
        file.write("\n" + "=" * 80 + "\n")
    except Exception as e:
        logging.error(f"Error writing data to file: {e}")

def main():
    """Main function - Following your template structure exactly"""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Fetch the page content
        page_content = fetch_webpage(page_url)
        if not page_content:
            raise ValueError("Failed to fetch webpage content")

        # Parse the page HTML
        soup = BeautifulSoup(page_content, "html.parser")

        # Scrape different sections - EXACTLY AS IN YOUR ORIGINAL CODE
        main_heading_data = scrape_main_heading(soup, page_url)
        wideblock_data = scrape_wideblock_content(soup, page_url)
        stat_box_data = scrape_stat_boxes(soup, page_url)

        # Combine all scraped data - EXACTLY AS IN YOUR ORIGINAL CODE
        scraped_data = []
        if main_heading_data:
            scraped_data.append(main_heading_data)
        scraped_data.extend(wideblock_data)
        scraped_data.extend(stat_box_data)

        # Write to file - EXACTLY AS IN YOUR ORIGINAL CODE
        with open(output_file, "w", encoding="utf-8") as file:
            logging.info(f"Writing output to: {output_file}")
            for data in scraped_data:
                write_to_txt(file, data)

        logging.info(f"Successfully saved data to {output_file}")
        logging.info(f"Scraped {len(scraped_data)} sections total")
        return True

    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        return False

if __name__ == "__main__":
    main()