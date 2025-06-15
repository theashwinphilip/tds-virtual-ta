from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up the WebDriver for Firefox (make sure to specify the correct path to your GeckoDriver)
driver = webdriver.Firefox(service=Service("geckodriver.exe"))


# Function to extract data from a single page
def extract_data_from_page():
    # Wait for the page to load
    time.sleep(2)  # Adjust sleep time as necessary

    # Extract course content
    courses = driver.find_elements(By.CLASS_NAME, 'course-class')  # Adjust class name as necessary
    for course in courses:
        title = course.find_element(By.TAG_NAME, 'h3').text  # Adjust tag as necessary
        description = course.find_element(By.CLASS_NAME, 'description-class').text  # Adjust class name as necessary
        print(f'Title: {title}, Description: {description}')

# Main function to navigate through pages
def main():
    driver.get('https://tds.s-anand.net/#/')

    # Wait for the main content to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'main-content-class')))  # Adjust class name as necessary

    # Extract data from the first page
    extract_data_from_page()

    # Navigate through subpages (if applicable)
    try:
        next_button = driver.find_element(By.CLASS_NAME, 'next-button-class')  # Adjust class name as necessary
        while next_button.is_enabled():
            next_button.click()
            extract_data_from_page()
            next_button = driver.find_element(By.CLASS_NAME, 'next-button-class')  # Adjust class name as necessary
    except Exception as e:
        print("No more pages or an error occurred:", e)

    # Close the driver
    driver.quit()

if __name__ == "__main__":
    main()
