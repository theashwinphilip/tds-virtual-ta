from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import json
from bs4 import BeautifulSoup
from datetime import datetime

EMAIL = "23f2001235@ds.study.iitm.ac.in"
PASSWORD = "philipcpim"
LOGIN_URL = "https://discourse.onlinedegree.iitm.ac.in/session"
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def login(driver):
    driver.get(LOGIN_URL)
    time.sleep(3)
    driver.find_element(By.ID, "login-account-name").send_keys(EMAIL)
    driver.find_element(By.ID, "login-account-password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]").click()
    time.sleep(5)

def scrape_threads(driver):
    posts = []
    driver.get(BASE_URL + "/latest")
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = soup.select("a.title")
    thread_links = [BASE_URL + link["href"] for link in links]

    for link in thread_links:
        driver.get(link)
        time.sleep(4)
        page = BeautifulSoup(driver.page_source, "html.parser")
        title = page.select_one("title").text.strip()
        all_posts = page.select("div.cooked")
        all_text = [p.get_text(separator="\n") for p in all_posts]

        date_elem = page.select_one("time")
        date_str = date_elem['datetime'][:10] if date_elem else '2025-01-01'
        post_date = datetime.strptime(date_str, "%Y-%m-%d")
        if datetime(2025, 1, 1) <= post_date <= datetime(2025, 4, 14):
            posts.append({
                "title": title,
                "url": link,
                "date": date_str,
                "posts": all_text
            })

    return posts

if __name__ == "__main__":
    driver = setup_driver()
    login(driver)
    data = scrape_threads(driver)
    driver.quit()

    with open("discourse_posts_logged_in.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(data)} threads to discourse_posts_logged_in.json")
