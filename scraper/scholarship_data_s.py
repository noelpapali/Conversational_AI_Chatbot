import logging
import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the logging configuration function
from logging_config import configure_logging


def setup_driver():
    """Set up and return a properly configured Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Determine the environment
    if os.getenv('GITHUB_ACTIONS'):
        # GitHub Actions environment - use WebDriver Manager
        service = Service(ChromeDriverManager().install())
    else:
        # Local development environment
        chrome_driver_path = "../chrome/chromedriver.exe"
        service = Service(executable_path=chrome_driver_path)

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def extract_main_heading(driver):
    """Extract the main heading from the page."""
    main_heading = driver.find_element(By.TAG_NAME, 'h1').text.strip()
    filename = main_heading.replace(" ", "_") + ".csv"  # Convert spaces to underscores and add .csv
    logging.info(f"Main heading extracted: {main_heading}")
    return filename

def extract_table_headers(driver):
    """Extract and filter table headers."""
    table = driver.find_element(By.ID, 'myTable')
    headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, 'th')]
    required_headers = ['Scholarship name', 'School', 'Academic Program', 'Status', 'Deadline']
    headers = [header for header in headers if header in required_headers]
    logging.info(f"Filtered headers: {headers}")
    logging.info(f"Number of headers: {len(headers)}")
    return headers

def extract_table_rows(driver, headers):
    """Extract rows from the table across all pages."""
    all_rows = []
    page_number = 1

    while True:
        logging.info(f"Processing page {page_number}...")

        table = driver.find_element(By.ID, 'myTable')
        rows = table.find_elements(By.TAG_NAME, 'tr')

        for row in rows:
            cells = [cell.text.strip() if cell.text.strip() else "" for cell in row.find_elements(By.TAG_NAME, 'td')]
            if len(cells) > 1:  # Skip the first column (the "+" button column)
                cells = cells[1:]

                # Ensure the row has the same number of columns as headers
                if len(cells) != len(headers):
                    logging.warning(f"Row has {len(cells)} columns, expected {len(headers)}. Padding with empty strings.")
                    cells += [""] * (len(headers) - len(cells))

                all_rows.append(cells)

        # Check for and click the "Next" button
        try:
            next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
            if "disabled" in next_button.get_attribute("class"):
                logging.info("Reached the last page.")
                break  # Exit loop if the "Next" button is disabled (last page)
            next_button.click()
            time.sleep(2)  # Wait for the next page to load
            page_number += 1
        except Exception as e:
            logging.error(f"Error: {e}")
            break  # Exit loop if no "Next" button is found

    return all_rows

def save_to_csv(data, headers, filename, output_dir):
    """Save the extracted data to a CSV file."""
    df = pd.DataFrame(data, columns=headers)
    logging.info(f"Total rows extracted: {len(data)}")

    os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
    output_file = os.path.join(output_dir, filename)
    df.to_csv(output_file, index=False)
    logging.info(f"File saved successfully at: {output_file}")

def main():
    # Configure logging
    configure_logging(log_file="scraping.log", log_level=logging.INFO)

    driver = None
    try:
        # Set up WebDriver
        driver = setup_driver()

        # Navigate to the target URL
        url = "https://www.utdallas.edu/costs-scholarships-aid/scholarships/listings/"
        driver.get(url)
        logging.info(f"Successfully navigated to: {url}")

        # Extract main heading and generate filename
        filename = extract_main_heading(driver)

        # Extract table headers
        headers = extract_table_headers(driver)

        # Extract table rows
        all_rows = extract_table_rows(driver, headers)

        # Save data to CSV
        output_dir = "../scraped_data"
        save_to_csv(all_rows, headers, filename, output_dir)

    except Exception as e:
        logging.error(f"An error occurred in main: {e}", exc_info=True)
    finally:
        # Close the browser
        if driver:
            driver.quit()
            logging.info("WebDriver closed.")

if __name__ == "__main__":
    main()