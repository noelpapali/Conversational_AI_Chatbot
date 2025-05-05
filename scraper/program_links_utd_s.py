import os
import json
import logging
from configparser import ConfigParser

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Import the logging configuration function
from logging_config import configure_logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Determine environment
is_github_env = os.environ.get('GITHUB_ACTIONS') == 'true'


# Output directories - local and git
local_output_dir = "../scraped_data"
git_output_dir = "scraped_data_git"
output_dir = git_output_dir if is_github_env else local_output_dir

# Output file path
output_file = os.path.join(output_dir, "utd_programs_links.json")

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

def fetch_program_links(driver, url):
    """Fetch program links from the given URL."""
    logging.info(f"Fetching main page: {url}")
    driver.get(url)

    # Wait for page to load fully
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Find all program links
    programs = driver.find_elements(By.CSS_SELECTOR, "a.degreetype")

    if not programs:
        logging.warning("No program links found.")
    else:
        logging.info(f"Found {len(programs)} program links.")

    # Extract program names and URLs
    return [{"name": program.text, "url": program.get_attribute("href")} for program in programs]

def save_to_json(data, output_file):
    """Save the extracted data to a JSON file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logging.info(f"Data successfully written to {output_file}")

def main():
    try:
        # Set up WebDriver
        driver = setup_driver()
        logging.info("WebDriver initialized successfully")
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")

        try:
            # URL of the webpage
            url = "https://www.utdallas.edu/academics/degrees/"

            # Fetch program links
            program_data = fetch_program_links(driver, url)

            # Save data to JSON
            save_to_json(program_data, output_file)
            logging.info(f"Data successfully saved to {output_file}")

        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}", exc_info=True)
            raise  # Re-raise the exception after logging

    except Exception as e:
        logging.error(f"Initialization error: {str(e)}", exc_info=True)
        raise
    finally:
        if 'driver' in locals():
            driver.quit()
            logging.info("WebDriver closed")

if __name__ == "__main__":
    main()