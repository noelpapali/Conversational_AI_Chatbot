import os
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the logging configuration function
from logging_config import configure_logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    """Set up and return the Selenium WebDriver with cross-environment support."""
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Determine the environment
    if os.getenv('GITHUB_ACTIONS'):
        # GitHub Actions environment
        service = Service(ChromeDriverManager().install())
    else:
        # Local development environment
        chrome_driver_path = "../chrome/chromedriver.exe"
        service = Service(executable_path=chrome_driver_path)

    return webdriver.Chrome(service=service, options=options)

def load_program_links(input_file):
    """Load program links from the existing JSON file."""
    with open(input_file, "r", encoding="utf-8") as f:
        program_links = json.load(f)
    logging.info(f"Loaded {len(program_links)} program links from {input_file}")
    return program_links

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
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=4, ensure_ascii=False)
    logging.info(f"Scraped data successfully written to {output_file}")

def main():
    # Configure logging
    configure_logging(log_file="scraping.log", log_level=logging.INFO)

    try:
        # Set up WebDriver
        driver = setup_driver()
        logging.info("WebDriver initialized successfully")

        # Define input and output files
        input_file = "../scraped_data/utd_programs_links.json"
        output_file = "../scraped_data/utd_programs_data.json"

        try:
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

        except Exception as e:
            logging.error(f"Error occurred: {e}")

    except Exception as e:
        logging.error(f"Initialization error: {str(e)}", exc_info=True)
        raise

    finally:
        if 'driver' in locals():
            driver.quit()
            logging.info("WebDriver closed")

if __name__ == "__main__":
    main()