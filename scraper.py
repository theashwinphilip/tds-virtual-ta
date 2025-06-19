#!/usr/bin/env python3
"""
Enhanced Data Scraper for TDS Course Content and Discourse Posts
This script scrapes course content from GitHub and Discourse posts with authentication.
"""

import asyncio
import json
import re
import subprocess
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import os

import httpx
from bs4 import BeautifulSoup
import markdown
from markdown.extensions import codehilite, fenced_code

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedTDSDataScraper:
    """Enhanced scraper with better error handling and data processing"""
    
    def __init__(self):
        self.course_base_url = "https://tds.s-anand.net"
        self.discourse_base_url = "https://discourse.onlinedegree.iitm.ac.in"
        self.github_repo = "https://github.com/sanand0/tools-in-data-science-public.git"
        self.discourse_username = os.getenv('DISCOURSE_USERNAME')
        self.discourse_password = os.getenv('DISCOURSE_PASSWORD')
        self.session = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True
        )
        if not self.discourse_username or not self.discourse_password:
            logger.error("Discourse credentials not found in .env file")
            raise ValueError("Missing DISCOURSE_USERNAME or DISCOURSE_PASSWORD")
    
    async def scrape_github_course_content(self) -> Dict[str, Any]:
        """Scrape course content from GitHub repository"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info("Cloning TDS course repository...")
                
                # Clone repository
                result = subprocess.run([
                    "git", "clone", "--depth", "1", self.github_repo, temp_dir
                ], capture_output=True, text=True, check=True)
                
                course_content = {}
                repo_path = Path(temp_dir)
                
                # Process markdown files
                md_files = list(repo_path.glob("*.md"))
                logger.info(f"Found {len(md_files)} markdown files")
                
                for md_file in md_files:
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            raw_content = f.read()
                        
                        # Convert markdown to HTML for better parsing
                        html_content = markdown.markdown(
                            raw_content, 
                            extensions=['codehilite', 'fenced_code', 'tables', 'toc']
                        )
                        
                        # Extract metadata
                        title = self._extract_title_from_markdown(raw_content) or md_file.stem
                        
                        course_content[md_file.name] = {
                            "title": title,
                            "filename": md_file.name,
                            "raw_content": raw_content,
                            "html_content": html_content,
                            "url": f"{self.course_base_url}#{md_file.stem}",
                            "last_updated": datetime.now().isoformat(),
                            "word_count": len(raw_content.split()),
                            "sections": self._extract_sections_from_markdown(raw_content)
                        }
                        
                    except Exception as e:
                        logger.error(f"Error processing {md_file}: {e}")
                        continue
                
                # Process additional files (notebooks, data files, etc.)
                additional_files = self._find_additional_course_files(repo_path)
                for file_path in additional_files:
                    try:
                        rel_path = file_path.relative_to(repo_path)
                        course_content[str(rel_path)] = {
                            "title": file_path.name,
                            "filename": file_path.name,
                            "type": file_path.suffix,
                            "url": f"https://github.com/sanand0/tools-in-data-science-public/blob/main/{rel_path}",
                            "last_updated": datetime.now().isoformat()
                        }
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        continue
                
                logger.info(f"Successfully scraped {len(course_content)} course files")
                return course_content
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            return {}
        except Exception as e:
            logger.error(f"Error scraping course content: {e}")
            return {}
    
    def _extract_title_from_markdown(self, content: str) -> Optional[str]:
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# '):
                return line[2:].strip()
        return None
    
    def _extract_sections_from_markdown(self, content: str) -> List[Dict[str, str]]:
        """Extract sections from markdown content"""
        sections = []
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip(),
                        "level": current_section.count('#')
                    })
                
                # Start new section
                current_section = line.strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip(),
                "level": current_section.count('#')
            })
        
        return sections
    
    def _find_additional_course_files(self, repo_path: Path) -> List[Path]:
        """Find additional course files (notebooks, datasets, etc.)"""
        patterns = ["*.ipynb", "*.csv", "*.json", "*.py", "*.yaml", "*.yml"]
        files = []
        
        for pattern in patterns:
            files.extend(repo_path.glob(pattern))
            files.extend(repo_path.glob(f"**/{pattern}"))
        
        # Filter out common non-course files
        exclude_patterns = [".git", "__pycache__", ".pytest_cache", "node_modules"]
        filtered_files = []
        
        for file_path in files:
            if not any(exclude in str(file_path) for exclude in exclude_patterns):
                filtered_files.append(file_path)
        
        return filtered_files
    
    async def scrape_discourse_posts_enhanced(self, 
                                             start_date: datetime = None, 
                                             end_date: datetime = None) -> Dict[str, Any]:
        """Scrape Discourse posts with authentication and date filtering"""
        if not start_date:
            start_date = datetime(2025, 1, 1)
        if not end_date:
            end_date = datetime(2025, 4, 14)
        
        try:
            # Log in to Discourse
            login_url = f"{self.discourse_base_url}/session"
            login_data = {
                'login': self.discourse_username,
                'password': self.discourse_password
            }
            login_response = await self.session.post(login_url, data=login_data)
            if login_response.status_code != 200:
                logger.error("Discourse login failed")
                return {}
            logger.info("Successfully logged into Discourse")

            # Scrape latest topics
            discourse_data = {}
            page = 1
            while True:
                topics_url = f"{self.discourse_base_url}/latest.json?page={page}"
                try:
                    response = await self.session.get(topics_url)
                    response.raise_for_status()
                    topics_data = response.json()
                except httpx.HTTPStatusError as e:
                    logger.error(f"Error fetching topics page {page}: {e}")
                    break
                
                if not topics_data.get('topic_list', {}).get('topics'):
                    break
                
                for topic in topics_data['topic_list']['topics']:
                    try:
                        created_at = datetime.strptime(topic['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        if start_date <= created_at <= end_date:
                            topic_id = topic['id']
                            posts = await self._fetch_topic_posts(str(topic_id), topic['title'])
                            discourse_data[f"topic-{topic_id}"] = {
                                "title": topic['title'],
                                "url": f"{self.discourse_base_url}/t/{topic['slug']}/{topic_id}",
                                "category": topic.get('category_id'),
                                "tags": topic.get('tags', []),
                                "created_at": topic['created_at'],
                                "last_activity": topic.get('last_posted_at'),
                                "posts_count": topic['posts_count'],
                                "views": topic['views'],
                                "posts": posts
                            }
                    except Exception as e:
                        logger.error(f"Error processing topic {topic.get('id')}: {e}")
                        continue
                
                page += 1
                if page > 10:  # Limit to 10 pages to avoid infinite loops
                    logger.info("Reached page limit for Discourse scraping")
                    break
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(1)
            
            logger.info(f"Successfully scraped {len(discourse_data)} Discourse topics")
            return discourse_data
         
        except Exception as e:
            logger.error(f"Error scraping Discourse posts: {e}")
            return {}
    
    async def _fetch_topic_posts(self, topic_id: str, title: str) -> List[Dict[str, Any]]:
        """Fetch posts for a specific topic"""
        try:
            posts_url = f"{self.discourse_base_url}/t/{topic_id}.json"
            response = await self.session.get(posts_url)
            response.raise_for_status()
            topic_data = response.json()
            
            posts = []
            for post in topic_data['post_stream']['posts']:
                try:
                    posts.append({
                        "post_number": post['post_number'],
                        "author": post['username'],
                        "created_at": post['created_at'],
                        "content": post['cooked'],  # HTML content
                        "likes": post.get('actions_summary', [{}])[0].get('count', 0),
                        "reply_to": post.get('reply_to_post_number')
                    })
                except Exception as e:
                    logger.error(f"Error processing post {post.get('post_number')} in topic {topic_id}: {e}")
                    continue
            
            return posts
         
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching posts for topic {topic_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching posts for topic {topic_id}: {e}")
            return []
    
    async def save_scraped_data(self, course_content: Dict, discourse_posts: Dict, output_dir: str = "data"):
        """Save scraped data to files"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Save course content
            course_file = output_path / "course_content.json"
            with open(course_file, 'w', encoding='utf-8') as f:
                json.dump(course_content, f, indent=2, ensure_ascii=False)
            
            # Save discourse posts
            discourse_file = output_path / "discourse_posts.json"
            with open(discourse_file, 'w', encoding='utf-8') as f:
                json.dump(discourse_posts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved to {output_path}")
        
        except Exception as e:
            logger.error(f"Error saving scraped data: {e}")
    
    async def close(self):
        """Close HTTP session"""
        try:
            await self.session.aclose()
            logger.info("HTTP session closed")
        except Exception as e:
            logger.error(f"Error closing HTTP session: {e}")

async def main():
    """Main function to run the scraper"""
    scraper = EnhancedTDSDataScraper()
    
    try:
        logger.info("Starting TDS data scraping...")
        
        # Scrape course content
        course_content = await scraper.scrape_github_course_content()
        
        # Scrape discourse posts
        discourse_posts = await scraper.scrape_discourse_posts_enhanced()
        
        # Save data
        await scraper.save_scraped_data(course_content, discourse_posts)
        
        logger.info("Scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())