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

# Load the program links from the existing JSON file
input_file = "../scraped_data/utd_programs_links.json"
output_file = "../scraped_data/utd_programs_data.json"

try:
    with open(input_file, "r", encoding="utf-8") as f:
        program_links = json.load(f)

    logging.info(f"Loaded {len(program_links)} program links from {input_file}")

    # Initialize a list to store all scraped data
    scraped_data = []

    for program in program_links:
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

            # Add the program data to the list
            scraped_data.append(program_data)
            logging.info(f"Successfully scraped data for program: {program_name}")

        except Exception as e:
            logging.error(f"Error scraping data for program {program_name}: {e}")

    # Save the scraped data to a new JSON file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=4, ensure_ascii=False)

    logging.info(f"Scraped data successfully written to {output_file}")

except Exception as e:
    logging.error(f"Error occurred: {e}")

finally:
    driver.quit()
    logging.info("WebDriver closed.")