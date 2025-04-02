import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

def fetch_webpage(url):
    """Fetch the webpage content."""
    response = requests.get(url)
    response.raise_for_status()  # Check for HTTP errors
    return response.content

def parse_html(content):
    """Parse the HTML content using BeautifulSoup."""
    return BeautifulSoup(content, 'html.parser')

def extract_tables(soup):
    """Extract all tables with the specified class."""
    return soup.find_all('figure', class_='wp-block-table is-style-stripes')

def clean_heading(heading):
    """Clean and format the heading text for use in filenames."""
    if heading:
        heading_text = heading.text.strip()
        return re.sub(r'[^\w\s-]', '', heading_text).strip().replace(' ', '_').lower()
    return None

def save_table_to_csv(table, heading_text, output_folder, i):
    """Extract and save a table to a CSV file."""
    try:
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
        heading_text_cleaned = clean_heading(heading_text) or f"table_{i + 1}"
        output_file = f"{heading_text_cleaned}.csv"
        output_path = os.path.join(output_folder, output_file)

        # Save the DataFrame to a CSV file
        df.to_csv(output_path, index=False)

        print(f"Table '{heading_text_cleaned}' extracted and saved to {output_path}")

    except Exception as e:
        print(f"Error processing table {i + 1}: {e}")

def main():
    # URL of the webpage
    url = "https://finaid.utdallas.edu/deadlines/"

    # Create a directory to save CSV files
    output_folder = "../tables"
    os.makedirs(output_folder, exist_ok=True)

    # Fetch and parse the webpage
    content = fetch_webpage(url)
    soup = parse_html(content)

    # Extract all tables
    tables = extract_tables(soup)

    # Loop through each table and extract data
    for i, table in enumerate(tables):
        # Extract the heading of the table
        heading = table.find_previous(['h2', 'h3'], class_='wp-block-heading')
        heading_text = heading.text.strip() if heading else f"Table {i + 1}"

        # Save the table to a CSV file
        save_table_to_csv(table, heading_text, output_folder, i)

    print("\nAll tables processed!")

if __name__ == "__main__":
    main()