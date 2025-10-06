import cloudscraper
from bs4 import BeautifulSoup


PAGEURL= "https://tuinzaden.eu/en/"
CATEGORYURL = "11-flower-seeds-seeds?resultsPerPage=160"

scraper = cloudscraper.create_scraper()
response = scraper.get(PAGEURL + CATEGORYURL)

soup = BeautifulSoup(response.text, "html.parser")

products = soup.find_all("article", class_="product-miniature")

if not products:
    print("No products found")
    exit(1)
else:
    for product in products:
        url = product.find("a", class_="thumbnail product-thumbnail", href=True)
        print(url["href"])
