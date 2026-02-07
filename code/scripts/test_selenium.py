
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def main():
    print("Initializing Chrome Options")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Impersonate a real browser
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    print("Starting WebDriver")
    try:
        driver = webdriver.Chrome(options=options)
        print("Driver started.")
        
        url = "https://www.doenetwork.org/cases/software/uid-geo-us-males.html"
        print(f"Navigating to {url}")
        driver.get(url)
        
        time.sleep(3) # Wait for potential redirects/checks
        
        title = driver.title
        print(f"Page Title: {title}")
        
        # Check for case links
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='main.html?id=']")
        print(f"Found {len(links)} case links.")
        
        if len(links) > 0:
            print("SUCCESS: Content loaded.")
            print(f"Sample Link: {links[0].get_attribute('href')}")
            
            # Check for NamUs patterns in the whole page text
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print("\n--- Index Page Text Sample ---")
            print(body_text[:2000])
            
            if "NamUs" in body_text:
                print("\n✅ 'NamUs' found in index page text!")
            else:
                print("\n❌ 'NamUs' NOT found in index page text.")
        else:
            print("FAILURE: No links found (Possible Block/Captcha).")
            print(f"Page Source Preview: {driver.page_source[:500]}")
            
        driver.quit()
        
    except Exception as e:
        print(f"Selenium Error: {e}")

if __name__ == "__main__":
    main()
