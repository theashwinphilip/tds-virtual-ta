from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import os
from urllib.parse import urljoin, urlparse

class TDSCompleteScraper:
    def __init__(self):
        # Configure Firefox with robust settings
        self.options = Options()
        self.options.headless = False  # Set to True after testing
        self.options.add_argument("--disable-dev-shm-usage")
        
        # Configure service
        self.service = Service('geckodriver.exe')
        
        # Initialize browser
        self.driver = self.init_driver()
        
        # Website information
        self.base_url = "https://tds.s-anand.net/"
        self.domain = urlparse(self.base_url).netloc
        self.visited_urls = set()
        self.scraped_data = []
        
        # Output configuration
        self.output_dir = "tds_scraped_data"
        os.makedirs(self.output_dir, exist_ok=True)

    def init_driver(self):
        """Initialize WebDriver with error handling"""
        try:
            driver = webdriver.Firefox(service=self.service, options=self.options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def safe_get(self, url, max_retries=3):
        """Robust URL loading with retries"""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
                self.restart_driver()
                time.sleep(2)
        return False

    def restart_driver(self):
        """Restart the browser session"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
        self.driver = self.init_driver()

    def scrape_website(self):
        """Main method to scrape all pages"""
        try:
            print("Starting complete website scrape...")
            
            # Start with base URL
            if not self.safe_get(self.base_url):
                raise Exception("Failed to load base URL")
            
            # Find all pages recursively
            self.crawl_and_scrape(self.base_url)
            
            # Save all collected data
            self.save_data()
            print("Website scraping completed successfully!")
            
        except Exception as e:
            print(f"Error during website scraping: {str(e)}")
        finally:
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    def crawl_and_scrape(self, url):
        """Recursively crawl and scrape all pages"""
        if url in self.visited_urls:
            return
            
        print(f"\nScraping: {url}")
        self.visited_urls.add(url)
        
        if not self.safe_get(url):
            print(f"Failed to load {url}, skipping...")
            return
            
        try:
            # Get page content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract main content
            page_data = self.extract_page_data(soup, url)
            self.scraped_data.append(page_data)
            
            # Find all links on page
            links = self.get_all_links(soup, url)
            
            # Scrape each new link
            for link in links:
                if link not in self.visited_urls:
                    self.crawl_and_scrape(link)
                    
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")

    def extract_page_data(self, soup, url):
        """Extract structured data from a page"""
        try:
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            
            # Special handling for different page types
            if 'tools' in url.lower():
                content_type = 'tools'
                tools = self.extract_tools(main_content)
            else:
                content_type = 'general'
                tools = []
            
            return {
                "url": url,
                "type": content_type,
                "title": soup.find('h1').get_text().strip() if soup.find('h1') else "",
                "headers": [h.get_text().strip() for h in main_content.find_all(['h1', 'h2', 'h3'])] if main_content else [],
                "paragraphs": [p.get_text().strip() for p in main_content.find_all('p')] if main_content else [],
                "lists": [li.get_text().strip() for li in main_content.find_all('li')] if main_content else [],
                "tools": tools,
                "content": main_content.get_text('\n', strip=True) if main_content else "",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return {
                "url": url,
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    def extract_tools(self, content):
        """Specialized extraction for tools listings"""
        tools = []
        if not content:
            return tools
            
        try:
            # Handle different tool listing formats
            tool_items = content.find_all(['li', 'div.tool'])
            
            for item in tool_items:
                try:
                    tool_text = item.get_text().strip()
                    if ':' in tool_text:
                        tool_name, tool_desc = tool_text.split(':', 1)
                    else:
                        tool_name = tool_text
                        tool_desc = ""
                        
                    tools.append({
                        "name": tool_name.strip(),
                        "description": tool_desc.strip(),
                        "subitems": [sub.get_text().strip() for sub in item.find_all('li')]
                    })
                except:
                    continue
                    
        except Exception as e:
            print(f"Error extracting tools: {str(e)}")
            
        return tools

    def get_all_links(self, soup, base_url):
        """Find all links on page that belong to the same domain"""
        links = set()
        
        for link in soup.find_all('a', href=True):
            try:
                href = link['href']
                
                # Skip empty or fragment links
                if not href or href.startswith('#'):
                    continue
                    
                # Convert relative to absolute URLs
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)
                
                # Only include links from same domain
                if urlparse(href).netloc == self.domain:
                    links.add(href)
                    
            except Exception as e:
                print(f"Error processing link: {str(e)}")
                continue
                
        return links

    def save_data(self):
        """Save all scraped data in multiple formats"""
        try:
            # Save JSON (full data)
            json_file = os.path.join(self.output_dir, "tds_complete_data.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.scraped_data, f, indent=2, ensure_ascii=False)
            
            # Save CSV (structured data)
            csv_file = os.path.join(self.output_dir, "tds_structured_data.csv")
            structured_data = []
            for page in self.scraped_data:
                structured_data.append({
                    "url": page.get('url'),
                    "type": page.get('type'),
                    "title": page.get('title'),
                    "header_count": len(page.get('headers', [])),
                    "paragraph_count": len(page.get('paragraphs', [])),
                    "tool_count": len(page.get('tools', [])),
                    "content_length": len(page.get('content', ''))
                })
            pd.DataFrame(structured_data).to_csv(csv_file, index=False)
            
            # Save visited URLs
            visited_file = os.path.join(self.output_dir, "visited_urls.txt")
            with open(visited_file, 'w') as f:
                f.write("\n".join(self.visited_urls))
            
            print(f"Data saved to:\n- {json_file}\n- {csv_file}\n- {visited_file}")
            
        except Exception as e:
            print(f"Error saving data: {str(e)}")

if __name__ == "__main__":
    scraper = TDSCompleteScraper()
    scraper.scrape_website()