import os
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Set up WebDriver
chrome_driver_path = "../chrome/chromedriver.exe"
service = Service(chrome_driver_path)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode (remove for debugging)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=service, options=options)

try:
    url = "https://www.utdallas.edu/academics/degrees/"
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
    program_data = [{"name": program.text, "url": program.get_attribute("href")} for program in programs]

    # Save data to JSON
    output_file = "../scraped_data/utd_programs_links.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(program_data, f, indent=4, ensure_ascii=False)

    logging.info(f"Data successfully written to {output_file}")

except Exception as e:
    logging.error(f"Error occurred: {e}")

finally:
    driver.quit()
    logging.info("WebDriver closed.")
