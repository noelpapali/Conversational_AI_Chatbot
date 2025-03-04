import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import pandas as pd

# Import the logging configuration function
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Set up Selenium WebDriver
service = Service("chrome/chromedriver.exe")  # Path to your ChromeDriver
driver = webdriver.Chrome(service=service)  # Use the service parameter
driver.get("https://www.utdallas.edu/costs-scholarships-aid/scholarships/listings/")

# Wait for the page to load
driver.implicitly_wait(10)

# Extract the main heading
main_heading = driver.find_element(By.TAG_NAME, 'h1').text.strip()
filename = main_heading.replace(" ", "_") + ".csv"  # Convert spaces to underscores and add .csv
logging.info(f"Main heading extracted: {main_heading}")  # Log main heading

# Initialize a list to store all rows
all_rows = []

# Extract table headers
table = driver.find_element(By.ID, 'myTable')
headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, 'th')]

# Filter required headers (exclude the first empty header)
required_headers = ['Scholarship name', 'School', 'Academic Program', 'Status', 'Deadline']
headers = [header for header in headers if header in required_headers]

# Add the new header for additional information
headers.append("Additional Information")
logging.info(f"Filtered headers: {headers}")  # Log filtered headers
logging.info(f"Number of headers: {len(headers)}")  # Log number of headers

# Loop through all pages
page_number = 1
while True:
    logging.info(f"Processing page {page_number}...")  # Log current page

    # Find the table
    table = driver.find_element(By.ID, 'myTable')

    # Extract rows from the current page
    rows = table.find_elements(By.TAG_NAME, 'tr')
    for row in rows:
        # Extract all cells in the row
        cells = [cell.text.strip() if cell.text.strip() else "" for cell in row.find_elements(By.TAG_NAME, 'td')]

        # Exclude the first column (the "+" button column)
        if len(cells) > 1:  # Ensure there are enough columns
            cells = cells[1:]  # Skip the first column

        if cells:  # Skip empty rows (e.g., header row)
            # Initialize additional information as empty
            additional_info = ""

            # Try to extract additional information
            try:
                # Find the "More Information" link
                more_info_link = row.find_element(By.CLASS_NAME, 'more-information-text')
                scholarship_id = more_info_link.get_attribute('href').split('#')[-1]

                # Locate the corresponding more-information-text table
                more_info_table = driver.find_element(By.ID, f'scholarship-more-information-{scholarship_id}')

                # Extract text from <p> and <li> tags
                paragraphs = more_info_table.find_elements(By.TAG_NAME, 'p')
                lists = more_info_table.find_elements(By.TAG_NAME, 'li')
                for p in paragraphs:
                    additional_info += p.text.strip() + " "
                for li in lists:
                    additional_info += li.text.strip() + " "

                # Clean up additional info
                additional_info = additional_info.strip()
            except Exception as e:
                logging.warning(f"Error extracting additional information for row: {e}")
                additional_info = ""  # Set to empty if extraction fails

            # Append the additional information to the row
            cells.append(additional_info)

            # Ensure the row has the same number of columns as headers
            if len(cells) != len(headers):
                logging.warning(f"Row has {len(cells)} columns, expected {len(headers)}. Padding with empty strings.")
                cells += [""] * (len(headers) - len(cells))  # Pad with empty strings

            all_rows.append(cells)

    # Check for and click the "Next" button
    try:
        next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
        if "disabled" in next_button.get_attribute("class"):
            logging.info("Reached the last page.")  # Log last page
            break  # Exit loop if the "Next" button is disabled (last page)
        next_button.click()
        time.sleep(2)  # Wait for the next page to load
        page_number += 1  # Increment page number
    except Exception as e:
        logging.error(f"Error: {e}")  # Log errors
        break  # Exit loop if no "Next" button is found

# Close the browser
driver.quit()

# Create a DataFrame
df = pd.DataFrame(all_rows, columns=headers)
logging.info(f"Total rows extracted: {len(all_rows)}")  # Log total rows

# Save to CSV
output_dir = "tables"
os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
output_file = os.path.join(output_dir, filename)  # Use the dynamic filename

# Save the DataFrame to CSV (without index)
df.to_csv(output_file, index=False)

logging.info(f"File saved successfully at: {output_file}")  # Log file save location