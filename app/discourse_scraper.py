import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"
FORUM_URL = f"{BASE_URL}/c/courses/tds-kb/34"
OUTPUT_FILE = "forum_data.json"

def scrape_forum():
    """Scrape the forum without authentication"""
    print(f"Scraping forum at {FORUM_URL}...")
    
    try:
        # Get the main forum page
        response = requests.get(FORUM_URL)
        response.raise_for_status()  # Raise exception for bad status codes
        
        soup = BeautifulSoup(response.text, 'html.parser')
        topics = []
        
        # Extract topic information
        for topic in soup.find_all('tr', class_='topic-list-item'):
            try:
                title_elem = topic.find('a', class_='title')
                title = title_elem.text.strip()
                link = urljoin(BASE_URL, title_elem['href'])
                
                topics.append({
                    'title': title,
                    'link': link,
                    'posts': topic.find('span', class_='posts').text.strip() if topic.find('span', class_='posts') else '',
                    'views': topic.find('span', class_='views').text.strip() if topic.find('span', class_='views') else '',
                    'activity': topic.find('span', class_='last-post').text.strip() if topic.find('span', class_='last-post') else '',
                    'tags': [tag.text.strip() for tag in topic.find_all('a', class_='discourse-tag')]
                })
            except Exception as e:
                print(f"Skipping topic due to error: {str(e)}")
                continue
        
        # Save results
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(topics, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully scraped {len(topics)} topics!")
        print(f"Data saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error scraping forum: {str(e)}")

if __name__ == "__main__":
    scrape_forum()