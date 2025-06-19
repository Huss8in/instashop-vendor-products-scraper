import os
import sys
import time
import random
import logging
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.keys import Keys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
sys.stderr = open('errors.log', 'w')

# ------------ Setup logging ------------ #
logging.basicConfig(
    filename='scraped_products.log',
    filemode='w',
    format='%(message)s',
    level=logging.INFO
)
row_counter = 1

# ------------ Start Timer ------------ #
start = time.time()

# ------------ Load Environment Variables ------------ #
load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT")
SHEET_ID = os.getenv("SHEET_ID")

# ------------ Get Base URL ------------ #
if len(sys.argv) == 2:
    BASE_URL = sys.argv[1]
else:
    # BASE_URL = "https://instashop.com/en-ae/client/max-muscle-90th-street"
    BASE_URL = "https://instashop.com/en-eg/client/the-grocer-garden-8-new-cairo"




# ------------ Initialize WebDriver ------------ #
service = Service(CHROMEDRIVER_PATH)
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 15)
actions = ActionChains(driver)

# ------------ Handle Cookies ------------ #
driver.get("https://instashop.com/en-eg")
try:
    time.sleep(2)
    wait.until(EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))).click()
    time.sleep(0.5)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-ripple.address.desktopWidth"))).click()
    time.sleep(0.5)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.appearance-filled.size-small.shape-round.status-basic.ng-star-inserted.nb-transition"))).click()

    search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search for a place']")))
    search_input.send_keys("Al Diyar Compound, New Cairo 1, Egypt")
    time.sleep(1)
    search_input.send_keys(Keys.ARROW_DOWN)
    search_input.send_keys(Keys.ENTER)
    search_input.send_keys(Keys.ENTER)
    
    time.sleep(3)
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.appearance-filled.size-small.shape-round.status-basic.ng-star-inserted.nb-transition"))).click()
        time.sleep(5)
    except Exception:
        pass
except Exception as e:
    print(f"Error during initial setup: {e}")

# ------------ Load Vendor Page ------------ #
time.sleep(3)
driver.get(BASE_URL)
time.sleep(random.uniform(5, 8))
vendor_name_element = driver.find_element(By.CLASS_NAME, "client-title")
vendor_name = vendor_name_element.text.strip()
print("----------------------------")
print(f"Vendor Name: {vendor_name}")
print("----------------------------")

# ------------ Extract Category Links ------------ #
soup = BeautifulSoup(driver.page_source, "html.parser")
categories = soup.find_all("div", class_="category-item ng-star-inserted")#[:2]

category_links = []
for cat in categories:
    a_tag = cat.find("a")
    if a_tag and a_tag.get("href"):
        category_links.append({
            "name": cat.get_text(strip=True),
            "url": "https://instashop.com" + a_tag["href"]
        })

# ~~~~~~~~~~~~~~~~~~~~~~~~~ TEST ~~~~~~~~~~~~~~~~~~~~~~~~~ #
# allowed_urls = {
#     # 'https://instashop.com/en-eg/client/the-grocer-garden-8-new-cairo/category/DkJopath6M',
#     'https://instashop.com/en-eg/client/the-grocer-garden-8-new-cairo/category/Q1KSfIRQar',
    
# }

# category_links = []
# for cat in categories:
#     a_tag = cat.find("a")
#     if a_tag and a_tag.get("href"):
#         full_url = "https://instashop.com" + a_tag["href"]
#         if full_url in allowed_urls:
#             category_links.append({
#                 "name": cat.get_text(strip=True),
#                 "url": full_url
#             })
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ------------ Scrolling Function ------------ #
def scroll_to_bottom():
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ------------ Scrape Product Data ------------ #
data = []
for category in tqdm(category_links, desc="Scraping categories"):
    print("=============================")
    time.sleep(10)
    driver.get(category["url"])
    print(f"Processing category: {category['name']}")
    
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product.mb-4.ng-star-inserted")))
        time.sleep(random.uniform(5, 8))
        scroll_to_bottom()
        time.sleep(random.uniform(2.5, 4.5))
        
        # Initial attempt
        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.product.mb-4.ng-star-inserted")

        # Retry if empty
        retry = 0
        while retry < 2:
            product_elements = driver.find_elements(By.CSS_SELECTOR, "div.product.mb-4.ng-star-inserted")
            if product_elements:
                break
            print(f"[{retry+1}] No products found in {category['name']}, retrying...")
            time.sleep(random.uniform(4, 6))
            driver.refresh()
            time.sleep(random.uniform(5, 8))
            scroll_to_bottom()
            retry += 1

            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product")))
            time.sleep(random.uniform(4, 6))
            scroll_to_bottom()
            product_elements = driver.find_elements(By.CSS_SELECTOR, "div.product.mb-4.ng-star-inserted")

        print(f"Found {len(product_elements)} products in {category['name']}")
        
        for product_element in product_elements:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", product_element)
                time.sleep(random.uniform(0.4, 0.9))
                
                soup = BeautifulSoup(product_element.get_attribute('outerHTML'), "html.parser")

                name = soup.find("div", class_="product-title")
                quantity = soup.find("div", class_="product-packaging-string")
                price = soup.find("div", class_="price-container d-flex justify-content-between")
                image = soup.find("img")
                
                description = ''
                extra_info = ''
                product_note = ''
                images = []
                
                try:
                    info_button = product_element.find_element(By.CSS_SELECTOR, "nb-icon.info")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", info_button)
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "nb-icon.info")))
                    actions.move_to_element(info_button).pause(0.3).click(info_button).perform()
                    time.sleep(random.uniform(1.5, 3.0))

                    # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.cdk-overlay-container")))
                    # time.sleep(3)
                    
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.cdk-overlay-container")))
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.text-secondary.pt-2.ng-star-inserted, div.swiper-wrapper, div[class*='pre-wrap']")))
                    time.sleep(1.5)
                    # ---------- #

                    overlay_html = driver.find_element(By.CSS_SELECTOR, "div.cdk-overlay-container").get_attribute('innerHTML')
                    overlay_soup = BeautifulSoup(overlay_html, "html.parser")

                    description_divs = overlay_soup.find_all("div", class_=lambda x: x and x.startswith("pre-wrap ng-tns-"))
                    for div in description_divs:
                        parent_style = div.find_parent("div", class_="ng-trigger-accordionItemBody")
                        style = parent_style.get('style', '') if parent_style else ''
                        if "visible" in style:
                            description = div.get_text(strip=True)
                        elif "hidden" in style:
                            extra_info = div.get_text(strip=True)

                    swiper_wrapper = overlay_soup.find("div", class_="swiper-wrapper")
                    if swiper_wrapper:
                        for img_tag in swiper_wrapper.find_all("img"):
                            if img_tag.has_attr("src"):
                                images.append(img_tag["src"].split("?")[0])

                    product_note_div = overlay_soup.find("div", class_="text-secondary pt-2 ng-star-inserted")
                    product_note = product_note_div.get_text(strip=True) if product_note_div else ''
                    
                    driver.find_element(By.TAG_NAME, "body").send_keys("\uE00C")
                    time.sleep(random.uniform(0.8, 1.2))

                except Exception:
                    pass

                data.append({
                    "category": category["name"],
                    "name": name.get_text(strip=True) if name else '',
                    "quantity": quantity.get_text(strip=True) if quantity else '',
                    "price": price.get_text(strip=True) if price else '',
                    "main_image_url": image["src"].split("?")[0] if image and "src" in image.attrs else '',
                    "description": f"{description}\n{product_note}" if product_note else description,
                    "extra_info": extra_info,
                    "images": ", ".join(images) if images else ''
                })
                # -------------------- TEST --------------------- #
                # print(f"{len(data)}")
                # print(f"category: {category['name']}")
                # print(f"name: {name.get_text(strip=True) if name else ''}")
                # print(f"quantity: {quantity.get_text(strip=True) if quantity else ''}")
                # print(f"price: {price.get_text(strip=True) if price else ''}")
                # print(f"main_image_url: {image['src'].split('?')[0] if image and 'src' in image.attrs else ''}")
                # print(f"description: {description.strip()}")
                # print(f"extra_info: {extra_info.strip()}")
                # print(f"images: {', '.join(images) if images else ''}")
                # print("----------------------------------------")
                # ----------------------------------------------- #
                logging.info(
                    f"{row_counter} | category: {category['name']} | name: {name.get_text(strip=True) if name else ''} | "
                    f"quantity: {quantity.get_text(strip=True) if quantity else ''} | price: {price.get_text(strip=True) if price else ''} | "
                    f"main_image_url: {image['src'].split('?')[0] if image and 'src' in image.attrs else ''} | "
                    f"description: {description.replace(chr(10), ' ')} | extra_info: {extra_info.replace(chr(10), ' ')} | "
                    f"images: {', '.join(images)}")
                row_counter += 1

            except Exception as e:
                print(f"Error processing product: {e}")
                continue
    except TimeoutException:
        print(f"Timeout waiting for products in category {category['name']}")
        continue
    except Exception as e:
        print(f"Error processing category {category['name']}: {e}")
        continue

# ------------ Close Driver ------------ #
driver.quit()

# ------------ Build DataFrame ------------ #
df = pd.DataFrame(data)
df.to_csv("backup", index=False)
df["price"] = df["price"].str.extract(r'(\d+\.?\d*)').astype(float)
df = df.replace([np.inf, -np.inf], np.nan)
df = df.fillna('')
df["images"] = df["images"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
print(df)

# ------------ Save to CSV ------------ #
csv_filename = f"{vendor_name.replace(' ', '_')}_instashop_products.csv"
df.to_csv(csv_filename, index=False)

# ------------ Upload to Google Sheets ------------ #
try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT, scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    sheet_name = f"{vendor_name.replace(' ', '_')}_instashop_products_{timestamp}"
    
    worksheet = sh.add_worksheet(
        title=sheet_name,
        rows=max(1000, len(df) + 100),
        cols=len(df.columns)
    )
    batch_size = 1000
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        if i == 0:
            worksheet.update([batch.columns.values.tolist()] + batch.values.tolist())
        else:
            worksheet.append_rows(batch.values.tolist())
    
    print(f"Data uploaded to new sheet: {sheet_name}")
except Exception as e:
    print(f"Error uploading to Google Sheets: {e}")

# ------------ Time Taken ------------ #
print("-----------------------------------------")
end = time.time()
total_seconds = end - start
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
print(f"Time taken: {minutes}m {seconds}s")
