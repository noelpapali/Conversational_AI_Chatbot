from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import logging
from logging_config import configure_logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Determine environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'

# Directory and file paths - local and git
local_output_dir = "../scraped_data"
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "utd_jindal_faculty_page.txt")


def setup_driver():
    """Set up and return the Selenium WebDriver with cross-environment support."""
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        # For both local and GitHub environments, use ChromeDriverManager with version matching
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver: {str(e)}")
        raise


def create_output_directory():
    """Create the output directory if it doesn't exist."""
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
    except Exception as e:
        logging.error(f"Failed to create directory {output_dir}: {e}")
        raise


def scrape_faculty_page(driver):
    """Scrape faculty page content and return structured data."""
    faculty_url = "https://jindal.utdallas.edu/faculty/"

    try:
        logging.info(f"Fetching faculty page: {faculty_url}")
        driver.get(faculty_url)
        time.sleep(5)  # Allow time for dynamic content to load

        faculty_soup = BeautifulSoup(driver.page_source, "html.parser")
        logging.info("Page successfully loaded and parsed")

        # --- 1. Extract All Headings and Corresponding Body Content ---
        headings_and_body = []
        for heading in faculty_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text(strip=True)
            body_content = []

            next_sibling = heading.find_next_sibling()
            while next_sibling and next_sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                body_content.append(next_sibling.get_text(strip=True))
                next_sibling = next_sibling.find_next_sibling()

            body_text = "\n".join(body_content).strip()
            if heading_text and body_text:
                headings_and_body.append(f"{heading_text}\n{body_text}\n")

        # --- 2. Extract Faculty Cards ---
        faculty_data = []
        faculty_cards = faculty_soup.select(".faculty-list-item")
        for card in faculty_cards:
            name = card.select_one(".faculty-name")
            title = card.select_one(".faculty-title")
            dept = card.select_one(".faculty-dept")
            link = card.select_one("a[href]")

            faculty_data.append(
                f"{name.text.strip() if name else 'N/A'}\n"
                f"{title.text.strip() if title else 'N/A'}\n"
                f"{dept.text.strip() if dept else 'N/A'}\n"
                f"{link['href'] if link else 'No Link'}\n"
            )

        # --- 3. Extract .stat-box.white.left50 Profiles ---
        profile_data = []
        staff_boxes = faculty_soup.select("div.stat-box.white.left50")
        for box in staff_boxes:
            name = box.select_one("h3 a")
            title = box.select_one("h4")
            links = box.select("p a")

            email = next((a.text for a in links if a["href"].startswith("mailto:")), "Email not found")
            phone = next((a.text for a in links if a["href"].startswith("tel:")), "Phone not found")
            office = next((a.text for a in links if "locator" in a["href"]), "Office not found")

            profile_data.append(
                f"{name.text.strip() if name else 'N/A'}\n"
                f"{title.text.strip() if title else 'N/A'}\n"
                f"{email}\n{phone}\n{office}\n"
            )

        # Combine all sections
        full_output = (
                "FACULTY PAGE CONTENT\n" + "\n".join(headings_and_body) + "\n\n"
                                                                          "FACULTY LISTING\n" + "\n".join(
            faculty_data) + "\n\n"
                            "STAFF PROFILES (Gray Wide Block)\n" + "\n".join(profile_data)
        )

        return full_output

    except Exception as e:
        logging.error(f"Error scraping faculty page: {e}")
        raise


def save_output(content, file_path):
    """Save scraped content to file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"Data successfully saved to: {file_path}")
    except Exception as e:
        logging.error(f"Failed to save output: {e}")
        raise


def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting faculty scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        driver = setup_driver()
        faculty_content = scrape_faculty_page(driver)
        save_output(faculty_content, output_file)

        logging.info("Faculty scraping completed successfully")
    except Exception as e:
        logging.error(f"Fatal error in faculty scraping: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.quit()
            logging.info("WebDriver closed")


if __name__ == "__main__":
    main()