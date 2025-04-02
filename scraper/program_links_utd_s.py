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

def setup_driver(chrome_driver_path):
    """Set up and return the Selenium WebDriver."""
    service = Service(chrome_driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (remove for debugging)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=service, options=options)

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
    # Configure logging
    configure_logging(log_file="scraping.log", log_level=logging.INFO)

    # Set up WebDriver
    chrome_driver_path = "../chrome/chromedriver.exe"
    driver = setup_driver(chrome_driver_path)

    try:
        # URL of the webpage
        url = "https://www.utdallas.edu/academics/degrees/"

        # Fetch program links
        program_data = fetch_program_links(driver, url)

        # Save data to JSON
        output_file = "../scraped_data/utd_programs_links.json"
        save_to_json(program_data, output_file)

    except Exception as e:
        logging.error(f"Error occurred: {e}")

    finally:
        # Close the WebDriver
        driver.quit()
        logging.info("WebDriver closed.")

if __name__ == "__main__":
    main()