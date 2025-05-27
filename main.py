import os
import sys
import time
import numpy as np
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gspread
from oauth2client.service_account import ServiceAccountCredentials

start = time.time()

# ------------ Load Env ------------ #
load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT")
SHEET_ID = os.getenv("SHEET_ID")

# ------------ Read URL from CLI ------------ #
if len(sys.argv) == 2:
    BASE_URL = sys.argv[1]
else:
    BASE_URL = "https://instashop.com/en-ae/client/max-muscle-90th-street"

# ------------ Setup WebDriver ------------ #
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service)
wait = WebDriverWait(driver, 10)

# ------------ Open main page and handle cookies ------------ #
driver.get("https://instashop.com/en-eg")
wait.until(EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))).click()
time.sleep(1)
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-ripple.address.desktopWidth"))).click()
time.sleep(1)
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.appearance-filled.size-small.shape-round.status-basic.ng-star-inserted.nb-transition"))).click()
time.sleep(10) # to edit the location if needed just write and click the name dont click the biutton 
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.appearance-filled.size-small.shape-round.status-basic.ng-star-inserted.nb-transition"))).click()
time.sleep(1)

# ------------ Scraping Vendor Categories Page ------------ #
driver.get(BASE_URL)
time.sleep(3)
soup = BeautifulSoup(driver.page_source, "html.parser")
categories = soup.find_all("div", class_="category-item ng-star-inserted")#[:2] # <======= 

category_links = []
for cat in categories:
    a_tag = cat.find("a")
    if a_tag and a_tag.get("href"):
        category_links.append({
            "name": cat.get_text(strip=True),
            "url": "https://instashop.com" + a_tag["href"]
        })
        
data = []
for category in tqdm(category_links, desc="Scraping categories"):
    driver.get(category["url"])
    time.sleep(4)
    print({category['name']})
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product")))
    
    # ------------------------------------------------------ #
    time.sleep(3)
    product_elements = driver.find_elements(By.CSS_SELECTOR, "div.product.mb-4.ng-star-inserted")#[:2] # <======= 

    # Loop through products
    for product_element in product_elements:
        soup = BeautifulSoup(product_element.get_attribute('outerHTML'), "html.parser")

        name = soup.find("div", class_="product-title")
        quantity = soup.find("div", class_="product-packaging-string")
        price = soup.find("div", class_="price-container d-flex justify-content-between")
        image = soup.find("img")
        extra_info = np.nan
        description = np.nan
        product_note = np.nan
        images = []

        try:
            product_element.click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.cdk-overlay-container")))
            time.sleep(2)

            overlay_html = driver.find_element(By.CSS_SELECTOR, "div.cdk-overlay-container").get_attribute('innerHTML')
            overlay_soup = BeautifulSoup(overlay_html, "html.parser")

            # ------------ Extract descriptions ------------ #
            description_divs = overlay_soup.find_all("div", class_=lambda x: x and x.startswith("pre-wrap ng-tns-"))
            for div in description_divs:
                parent_style = div.find_parent("div", class_="ng-trigger-accordionItemBody")
                style = parent_style.get('style', '') if parent_style else ''
                if "visible" in style:
                    description = div.get_text(strip=True)
                elif "hidden" in style:
                    extra_info = div.get_text(strip=True)
            # ------------ Extract Images URLs ------------ #
            swiper_wrapper = overlay_soup.find("div", class_="swiper-wrapper")
            if swiper_wrapper:
                for img_tag in swiper_wrapper.find_all("img"):
                    if img_tag.has_attr("src"):
                        images.append(img_tag["src"].split("?")[0])

            # ------------ Extract Note ------------ #
            product_note_div = overlay_soup.find("div", class_="text-secondary pt-2 ng-star-inserted")
            product_note = product_note_div.get_text(strip=True) if product_note_div else np.nan
    
            driver.find_element(By.TAG_NAME, "body").send_keys("\uE00C")
            time.sleep(1)

        except Exception as e:
            print(f"Error extracting overlay: {e}")

        data.append({
            "category": category["name"],
            "name": name.get_text(strip=True) if name else np.nan,
            "quantity": quantity.get_text(strip=True) if quantity else np.nan,
            "price": price.get_text(strip=True) if price else np.nan,
            "main_image_url": image["src"].split("?")[0] if image and "src" in image.attrs else np.nan,
            # "note":product_note,
            "description": f"{description}\n{product_note}" if product_note else description,
            "extra_info": extra_info,
            "images": images
        })

driver.quit()

# ------------ Convert to DataFrame ------------ #
df = pd.DataFrame(data)
# convert to float
df["price"] = df["price"].str.extract(r'(\d+\.?\d*)').astype(float) 

df = df.replace([np.inf, -np.inf], np.nan)
df = df.fillna('')

#
df["images"] = df["images"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")

print(df)

# ------------ Save to CSV ------------ #
df.to_csv("instashop_data.csv", index=False)

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

# ------------ Time taken ------------ #
print("-----------------------------------------")
end = time.time()
print(f"Time taken: {end - start:.2f} seconds")