import os
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from logging_config import configure_logging

# Configure logging
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

# Input and output files
input_file = os.path.join(output_dir, "utd_programs_links.json")
output_file = os.path.join(output_dir, "utd_programs_data.json")


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


def load_program_links(input_file):
    """Load program links from the existing JSON file."""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            program_links = json.load(f)
        logging.info(f"Loaded {len(program_links)} program links from {input_file}")
        return program_links
    except Exception as e:
        logging.error(f"Error loading program links: {e}")
        raise


def scrape_program_data(driver, program):
    """Scrape data for a single program."""
    program_name = program["name"]
    program_url = program["url"]
    logging.info(f"Scraping data for program: {program_name}")

    try:
        # Navigate to the program URL
        driver.get(program_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Extract the program name from the <h1> tag
        h1_tag = driver.find_element(By.TAG_NAME, "h1")
        program_title = h1_tag.text.strip()
        logging.info(f"Extracted program title: {program_title}")

        # Find all <h2> headings
        headings = driver.find_elements(By.CSS_SELECTOR, "h2.wp-block-heading")
        logging.info(f"Found {len(headings)} headings for program: {program_name}")

        # Extract data under each heading
        program_data = {
            "degreelevel": program_name,
            "program_name": program_title  # Add the program name from <h1>
        }
        for heading in headings:
            heading_text = heading.text.strip()

            # Initialize a list to store content under the heading
            content = []

            # Find the next sibling elements until the next <h2>
            sibling = heading.find_element(By.XPATH, "following-sibling::*[1]")
            while sibling and sibling.tag_name != "h2":
                content.append(sibling.text.strip())
                try:
                    sibling = sibling.find_element(By.XPATH, "following-sibling::*[1]")
                except:
                    break  # Exit if no more siblings

            # Add the heading and its content to the program data
            program_data[heading_text] = content

        logging.info(f"Successfully scraped data for program: {program_name}")
        return program_data

    except Exception as e:
        logging.error(f"Error scraping data for program {program_name}: {e}")
        return None


def save_scraped_data(scraped_data, output_file):
    """Save the scraped data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
        logging.info(f"Scraped data successfully written to {output_file}")
    except Exception as e:
        logging.error(f"Error saving scraped data: {e}")
        raise


def main():
    """Main function to orchestrate the scraping process."""
    try:
        logging.info(f"Starting scraping in {'GitHub Actions' if is_github_env else 'local'} environment")
        create_output_directory()

        # Set up WebDriver
        driver = setup_driver()
        logging.info("WebDriver initialized successfully")

        # Load program links
        program_links = load_program_links(input_file)

        # Initialize a list to store all scraped data
        scraped_data = []

        # Scrape data for each program
        for program in program_links:
            program_data = scrape_program_data(driver, program)
            if program_data:
                scraped_data.append(program_data)

        # Save the scraped data to a JSON file
        save_scraped_data(scraped_data, output_file)

        logging.info("Scraping completed successfully")

    except Exception as e:
        logging.error(f"Fatal error in main process: {e}")
        raise

    finally:
        if 'driver' in locals():
            driver.quit()
            logging.info("WebDriver closed")


if __name__ == "__main__":
    main()