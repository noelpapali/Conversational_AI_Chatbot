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
main_page_url = "https://jindal.utdallas.edu/news/"

# Output directory and file
output_dir = "../scraped_data"
output_file = os.path.join(output_dir, "news_page_data.txt")

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

def extract_news_posts(soup):
    """Extract news posts from the page."""
    posts = soup.find_all("div", class_="post")
    news_data = []
    for post in posts:
        post_data = {}

        # Extract title
        title = post.find("h3", class_="sans")
        if title:
            post_data["title"] = title.get_text(strip=True)
            post_data["title_link"] = title.find("a")["href"] if title.find("a") else None

        # Extract excerpt
        excerpt = post.find("p", class_="the-excerpt")
        if excerpt:
            post_data["excerpt"] = excerpt.get_text(strip=True)

        # Extract meta details (date and categories)
        meta_details = post.find("p", class_="meta-details")
        if meta_details:
            post_data["meta_details"] = meta_details.get_text(strip=True)

        # Extract image URL
        image = post.find("img")
        if image:
            post_data["image_url"] = image["src"]

        news_data.append(post_data)
    return news_data

def scrape_page(url, file):
    """Scrape content from a page and write it to the file."""
    logging.info(f"Scraping page: {url}")
    content = fetch_webpage(url)
    if not content:
        return

    soup = BeautifulSoup(content, "html.parser")

    # Write the URL to the file
    file.write(f"URL: {url}\n\n")

    # Extract and write news posts
    news_posts = extract_news_posts(soup)
    if news_posts:
        file.write("News Posts:\n")
        for post in news_posts:
            file.write(f"Title: {post.get('title', 'N/A')}\n")
            file.write(f"Title Link: {post.get('title_link', 'N/A')}\n")
            file.write(f"Excerpt: {post.get('excerpt', 'N/A')}\n")
            file.write(f"Meta Details: {post.get('meta_details', 'N/A')}\n")
            file.write(f"Image URL: {post.get('image_url', 'N/A')}\n")
            file.write("\n" + "=" * 50 + "\n\n")

def main():
    """Main function to orchestrate the scraping process."""
    create_output_directory()

    # Fetch the main page content
    main_page_content = fetch_webpage(main_page_url)
    if not main_page_content:
        return

    # Parse the main page HTML
    main_soup = BeautifulSoup(main_page_content, "html.parser")

    # Open the output file to write the scraped data
    with open(output_file, "w", encoding="utf-8") as file:
        logging.info(f"Opened file for writing: {output_file}")

        # Scrape the main page
        scrape_page(main_page_url, file)

    logging.info(f"Data scraped successfully and saved to '{output_file}'")

if __name__ == "__main__":
    main()