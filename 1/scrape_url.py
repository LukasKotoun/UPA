import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()

url_page1 = "https://www.bike-discount.de/en/bike?p=1&o=14&n=100"
url_page2 = "https://www.bike-discount.de/en/bike?p=2&o=14&n=100" 
resp_page1 = scraper.get(url_page1)
resp_page2 = scraper.get(url_page2)
soup_page1 = BeautifulSoup(resp_page1.text, "html.parser")
soup_page2 = BeautifulSoup(resp_page2.text, "html.parser")

products1 = soup_page1.find_all("div", class_="box--content")
products2 = soup_page2.find_all("div", class_="box--content")
products = products1 + products2

if not products:
    raise ValueError("No products found")

for product in products:
    url = product.find("a", class_="product--title", href=True)
    print(url["href"])

