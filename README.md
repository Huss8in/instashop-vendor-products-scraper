# Instashop Product Scraper

## Setup Instructions

- Install all dependencies from the `requirements.txt` file:
```bash
  pip install -r requirements.txt
```

- Install ChromeDriver and add its path to the .env file:
```bash
  CHROMEDRIVER_PATH=path/to/chromedriver.exe
```
- Create a new Google Sheet and share it with your service account email.
Add the service account credentials file path and Google Sheet ID to the .env file:
```bash
  SERVICE_ACCOUNT=path/to/service_account.json
  SHEET_ID=your_google_sheet_ide
```

## Usage
Run the script with the vendor URL in Instashop (the page containing all vendor categories):
```bash
    python product_scraper.py <url_of_vendor_in_instashop>
```

- The script extracts all vendor products by category, retrieving:
```bash
    Product_name    Quantity    Price   Image_src
```