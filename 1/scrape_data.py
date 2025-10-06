#!/usr/bin/python3

import sys
from typing import Optional, Sequence, Any
from bs4 import BeautifulSoup, element
from dataclasses import dataclass
import cloudscraper
from time import sleep



def any_to_tsv(value: Any):
    str_value = str(value).replace("\t", " ") # TODO: escape sanitization, ...
    return str_value


def to_tsv_colname(name: str):
    s = name[0].upper() + name[1:]
    return " ".join(s.split("_"))


def to_tsv_header(fields: dict):
    tsv_header = "\t".join(map(to_tsv_colname, fields))
    return tsv_header


def to_tsv_row(row: dict):
    tsv_row = "\t".join((any_to_tsv(value) for value in row.values()))
    return tsv_row


@dataclass
class Product:
    name: str | None
    price: str | None
    brand: str | None
    collection: str | None
    category: str | None
    planting_time: str | None
    flowering_period: str | None
    height: str | None
    color: str | None

    __tsv_store_order = ('name', 
                         'price',
                         'brand',
                         'collection',
                         'category',
                         'planting_time',
                         'flowering_period',
                         'height',
                         'color'
                         # TODO: more specifications
                         )
    def to_tsv_row(self):
        attr_dict = {attr: getattr(self, attr) for attr in self.__tsv_store_order}
        return to_tsv_row(attr_dict)
    
    @classmethod
    def to_tsv_header(self):
        return to_tsv_header(self.__tsv_store_order)


def extract_table_rows(table: element.Tag) -> dict[str, str]:
    rows = {
        row.find("dt", class_="product-specs-name").text.strip().lower().replace(':','').replace(' ', '_') :
        row.find("dd", class_="product-specs-value").text.strip()
        for row in table.find_all("div", class_="product-specs-row")}
    return rows


def extract_specs(page: BeautifulSoup) -> dict[str, str]:
    specs = {}
    tables = [extract_table_rows(table) for table in page.find_all("dl", class_="product-specs")]
    for table in tables:
        specs.update(table)
    return specs


def scrape_product(soup) -> Product:
    name = soup.find("h1", itemprop="name").text.strip()
    price = soup.find("span", itemprop="price").text.strip()
    specs = extract_specs(soup)
    
    return Product(name=name,
                   price=price,
                   brand=specs.get("brand", None),
                   collection=specs.get("collection", None),
                   category=specs.get("category", None),
                   planting_time=specs.get("planting_time", None),
                   flowering_period=specs.get("flowering_period", None),
                   height=specs.get("height", None),
                   color=specs.get("color", None)
                )


def main(argv: Optional[Sequence[str]] = None) -> int:
    scraper = cloudscraper.create_scraper()

    for url in sys.stdin.readlines():
        url = url.replace("\n", "")
        page = scraper.get(url)
        if (not page.ok):
            continue

        soup = BeautifulSoup(page.text, "html.parser")
        product = scrape_product(soup)
        print(product.to_tsv_row())
        sleep(1)

    return 0


if __name__ == "__main__":  
    sys.exit(main(sys.argv))