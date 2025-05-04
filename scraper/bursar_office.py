import os
import requests
import logging
from bs4 import BeautifulSoup
from configparser import ConfigParser
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


class BursarScraper:
    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config.ini')
        self.page_url = "https://bursar.utdallas.edu/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        # Setup output directories
        self.local_output_dir = "../scraped_data"
        self.git_output_dir = "scraped_data_git"
        self.is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'
        self.output_dir = self.git_output_dir if self.is_github_env else self.local_output_dir
        self.output_file = os.path.join(self.output_dir, "bursar_data.txt")

        logging.info(f"Environment: {'GitHub Actions' if self.is_github_env else 'Local'}")
        logging.info(f"Output directory: {self.output_dir}")

    def create_output_directory(self):
        """Create output directory if it doesn't exist."""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logging.info(f"Created directory: {self.output_dir}")
        except Exception as e:
            logging.error(f"Failed to create directory: {e}")
            raise

    def fetch_webpage(self, url, retries=3):
        """Fetch webpage content with retries and timeout handling."""
        for attempt in range(retries):
            try:
                logging.info(f"Attempt {attempt + 1}: Fetching {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                logging.info("Successfully retrieved webpage")
                return response.content
            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == retries - 1:
                    logging.error(f"All attempts failed for {url}")
                    return None

    def extract_content(self, soup):
        """Extract and structure content from BeautifulSoup object."""
        content = []
        main_content = soup.find("div", role="main") or soup

        # Extract all sections systematically
        for element in main_content.find_all(True):
            if element.name in ["h1", "h2", "h3"]:
                content.append(f"\nHeading {element.name.upper()}: {element.get_text(strip=True)}")
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    links = [f"{a.get_text(strip=True)} (URL: {urljoin(self.page_url, a['href'])})"
                             for a in element.find_all('a', href=True)]
                    content.append(f"Paragraph: {text}" + (f"\n  Links: {', '.join(links)}" if links else ""))
            elif element.name == "ul":
                items = []
                for li in element.find_all("li"):
                    link = li.find('a', href=True)
                    item_text = li.get_text(strip=True)
                    if link:
                        items.append(f"  - {item_text} (URL: {urljoin(self.page_url, link['href'])})")
                    else:
                        items.append(f"  - {item_text}")
                if items:
                    content.append("List:\n" + "\n".join(items))
            elif element.name == "table":
                rows = []
                for row in element.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
                    rows.append(" | ".join(cells))
                if rows:
                    content.append("Table:\n" + "\n".join(rows))

        return "\n".join(filter(None, content))

    def scrape_page(self):
        """Main scraping method that orchestrates the process."""
        try:
            self.create_output_directory()

            content = self.fetch_webpage(self.page_url)
            if not content:
                raise ValueError("Failed to fetch webpage content")

            soup = BeautifulSoup(content, "html.parser")
            extracted_content = self.extract_content(soup)

            # Save to file
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(f"URL: {self.page_url}\n\n")
                f.write(extracted_content)

            # Print summary
            print("\n=== SCRAPING SUMMARY ===")
            print(f"Source URL: {self.page_url}")
            print(f"Content saved to: {self.output_file}")
            print(f"Content length: {len(extracted_content)} characters")
            print("\n=== SAMPLE CONTENT ===")
            print(extracted_content[:500] + "..." if len(extracted_content) > 500 else extracted_content)

            return True

        except Exception as e:
            logging.error(f"Scraping failed: {str(e)}")
            return False


if __name__ == "__main__":
    scraper = BursarScraper()
    success = scraper.scrape_page()
    exit(0 if success else 1)