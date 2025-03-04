import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

# URL of the webpage
url = "https://finaid.utdallas.edu/deadlines/"

# Send a GET request to the webpage
response = requests.get(url)
response.raise_for_status()  # Check for HTTP errors

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, 'html.parser')

# Find all tables with the class 'wp-block-table is-style-stripes'
tables = soup.find_all('figure', class_='wp-block-table is-style-stripes')

# Create a directory to save CSV files
output_folder = "../tables"
os.makedirs(output_folder, exist_ok=True)

# Loop through each table and extract data
for i, table in enumerate(tables):
    try:
        # Extract the heading of the table
        heading = table.find_previous(['h2', 'h3'], class_='wp-block-heading')
        heading_text = heading.text.strip() if heading else f"Table {i + 1}"

        # Extract table headers
        headers = [header.text.strip() for header in table.find_all('th')]

        # Extract table rows
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip the header row
            cells = row.find_all('td')
            if len(cells) == len(headers):  # Ensure the row has the correct number of cells
                rows.append([cell.text.strip() for cell in cells])

        # Convert the data into a DataFrame
        df = pd.DataFrame(rows, columns=headers)

        # Define the output file name
        heading_text_cleaned = re.sub(r'[^\w\s-]', '', heading_text).strip().replace(' ', '_').lower()
        output_file = f"{heading_text_cleaned}.csv"
        output_path = os.path.join(output_folder, output_file)

        # Save the DataFrame to a CSV file
        df.to_csv(output_path, index=False)

        print(f"Table '{heading_text}' extracted and saved to {output_path}")

    except Exception as e:
        print(f"Error processing table {i + 1}: {e}")

print("\nAll tables processed!")