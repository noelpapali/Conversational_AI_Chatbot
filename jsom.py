import requests
from bs4 import BeautifulSoup

# URL of the JSOM page
url = "https://jindal.utdallas.edu/"

# Send a GET request to fetch the page content
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Extract all links on the page
links = soup.find_all('a', href=True)
for link in links:
    print(link['href'])