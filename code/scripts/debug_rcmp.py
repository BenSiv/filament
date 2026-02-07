
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

url = "https://www.services.rcmp-grc.gc.ca/missing-disparus/case-dossier.jsf?case=2014006179&lang=en"
print(f"Fetching {url}")
driver.get(url)

with open("data/raw/debug_case.html", "w") as f:
    f.write(driver.page_source)

print("Dumped HTML to debug_case.html")
driver.quit()
