import sys
import os
import time
import numpy as np
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------ Load Env ------------ #
load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT")
SHEET_ID = os.getenv("SHEET_ID")

if not CHROMEDRIVER_PATH or not SERVICE_ACCOUNT or not SHEET_ID:
    raise ValueError("Missing one or more required environment variables in .env")

# ------------ Read URL from CLI ------------ #
if len(sys.argv) != 2:
    print("Usage: python instashop_scraper.py <INSTASHOP_URL>")
    sys.exit(1)

BASE_URL = sys.argv[1]

# ------------ Setup WebDriver ------------ #
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service)
driver.get(BASE_URL)
time.sleep(5)

# ------------ Parse Categories ------------ #
soup = BeautifulSoup(driver.page_source, "html.parser")
categories = soup.find_all("div", class_="category-item ng-star-inserted")

category_links = []
for cat in categories:
    a_tag = cat.find("a")
    if a_tag and a_tag.get("href"):
        category_links.append({
            "name": cat.get_text(strip=True),
            "url": "https://instashop.com" + a_tag["href"]
        })

# ------------ Scrape Products ------------ #
all_data = []
for category in tqdm(category_links, desc="Scraping categories"):
    driver.get(category["url"])
    time.sleep(10)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    products = soup.find_all("div", class_="product mb-4 ng-star-inserted")

    for product in products:
        name = product.find("div", class_="product-title")
        quantity = product.find("div", class_="product-packaging-string")
        price = product.find("div", class_="price-container d-flex justify-content-between")
        image = product.find("img")

        all_data.append({
            "Category": category["name"],
            "Name": name.get_text(strip=True) if name else np.nan,
            "Quantity": quantity.get_text(strip=True) if quantity else np.nan,
            "Price": price.get_text(strip=True) if price else np.nan,
            "Image": image["src"] if image and "src" in image.attrs else np.nan
        })

driver.quit()

# ------------ Convert to DataFrame ------------ #
df = pd.DataFrame(all_data)

# ------------ Upload to Google Sheets ------------ #
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT, scope)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

# Clear sheet and update with new data
worksheet.clear()
worksheet.update([df.columns.values.tolist()] + df.values.tolist())