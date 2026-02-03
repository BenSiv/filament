"""
Podscribe Scraper.
"""

import logging
import time
from typing import Iterator

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from code.extraction.podcasts import PodcastTranscript

logger = logging.getLogger(__name__)

class PodscribeClient:
    """
    Client for fetching transcripts from Podscribe.
    """
    
    BASE_URL = "https://app.podscribe.com"
    
    def __init__(self):
        """Initialize Selenium driver options."""
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Ensure we point to the installed chromium if needed, but standard should work
        # self.chrome_options.binary_location = "/usr/bin/chromium"

    def fetch_series_transcripts(self, series_id: str, limit: int = 10) -> Iterator[PodcastTranscript]:
        """
        Fetch transcripts for a series.
        
        Args:
            series_id: Podscribe series ID (e.g., '870')
            limit: Max episodes to process
        """
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            series_url = f"{self.BASE_URL}/series/{series_id}"
            logger.info(f"Navigating to {series_url}")
            driver.get(series_url)
            
            # Wait for episodes to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'episode-row')] | //a[contains(@href, '/episode/')]"))
            )
            
            # Find episode links
            # Based on inspection, episodes are likely links or divs.
            # We need to grab them first effectively. 
            # Note: The browser agent saw links. Let's find links containing /episode/
            episode_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/episode/')]")
            
            # De-duplicate and limit
            episode_urls = []
            seen = set()
            for el in episode_elements:
                url = el.get_attribute("href")
                if url and url not in seen and f"/series/{series_id}" not in url:
                     # Some links might be back to series, ensure it's an episode
                     episode_urls.append(url)
                     seen.add(url)
            
            logger.info(f"Found {len(episode_urls)} episodes. Processing top {limit}...")
            
            for url in episode_urls[:limit]:
                try:
                    transcript = self._process_episode(driver, url)
                    if transcript:
                        yield transcript
                except Exception as e:
                    logger.error(f"Failed to process {url}: {e}")

        except TimeoutException:
            logger.error("Timeout waiting for episodes.")
            # driver.save_screenshot("debug_timeout.png")
            print("DEBUG: Page Title:", driver.title)
            print("DEBUG: Page Source Snippet:\n", driver.page_source[:5000]) 
            raise
                    
        finally:
            driver.quit()

    def _process_episode(self, driver: webdriver.Chrome, url: str) -> PodcastTranscript | None:
        """Process a single episode page."""
        logger.info(f"Processing {url}")
        driver.get(url)
        
        # Wait for transcript content
        # Check for spans that hold text
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "span"))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for transcript on {url}")
            return None
            
        # Extract Title
        try:
            # Title is usually h1 or specific class
            title = driver.title 
            # Clean up title "Episode Name - Podscribe"
            title = title.replace(" - Podscribe", "")
        except:
            title = "Unknown Title"
            
        # Scroll down to trigger lazy load? 
        # Browser agent showed we might need to scroll.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) # Allow load
        
        # Extract text
        # Strategy: Find the main transcript container or just grab all text spans that look like transcript
        # Heuristic: Speaker blocks have timestamps.
        # But simply: grab all text from the specific container if we can ID it.
        # If not, grab all text and clean. 
        # Let's try to get specific speaker blocks if possible, or just huge text blob.
        
        # Broad approach: get all meaningful text
        # Refinement: Browser agent saw <span> elements for words.
        # We can try to get all text from the "transcript-container" if it exists, or body.
        
        # Let's try to find a container with many spans
        # or just get text from body but that includes menu.
        
        # Better: Look for timestamp patterns or specific classes. 
        # Since I assume standard podscribe structure:
        
        try:
           # Attempt to find the main content area.
           # Often distinct from nav.
           # Let's assume there's a main div.
           # Or just grab the text
           
           # Get all text from divs that are NOT nav/header/footer
           # For now, let's just grab the whole body text and assume we can clean later?
           # No, that's messy.
           # Let's target the spans.
           spans = driver.find_elements(By.TAG_NAME, "span")
           # Filter spans that look like words (not UI elements)
           # This is fuzzy.
           
           # Let's rely on the verification step to refine selectors.
           # I'll dump the text of spans that are within a likely content div.
           
           # Using XPATH to find a div containing many spans?
           content_div = driver.find_element(By.XPATH, "//div[count(span) > 50] | //div[contains(@class, 'transcript')]")
           text = content_div.text
           
        except NoSuchElementException:
           # Fallback
           text = driver.find_element(By.TAG_NAME, "body").text
           
        return PodcastTranscript(
            video_id=url.split("/")[-1].split("?")[0], # Approximate ID
            channel_name="Podscribe Series",
            title=title,
            text=text,
            source_url=url
        )
