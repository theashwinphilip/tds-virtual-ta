from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os

BASE_URL = "https://tds.s-anand.net/#/"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def save_html(name, html):
    os.makedirs("tds_pages", exist_ok=True)
    with open(f"tds_pages/{name}.html", "w", encoding="utf-8") as f:
        f.write(html)

def scrape_tds_site():
    driver = setup_driver()
    driver.get(BASE_URL)
    time.sleep(5)  # Let JS load

    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = driver.find_elements("xpath", "//a[contains(@href, '#/')]")
    seen = set()

    for link in links:
        href = link.get_attribute("href")
        if href and href not in seen:
            seen.add(href)
            try:
                driver.get(href)
                time.sleep(3)
                save_html(href.split("#/")[-1].replace("/", "_"), driver.page_source)
            except:
                continue

    driver.quit()

if __name__ == "__main__":
    scrape_tds_site()
