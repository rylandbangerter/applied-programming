from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time

service = Service("C:/WebDriver/chromedriver.exe")  # Update this path to your actual chromedriver.exe location
driver = webdriver.Chrome(service=service)
driver.get("https://www.baseball-reference.com/search/search.fcgi?search=Shohei+Ohtani")
time.sleep(5)  # Wait for page to load

# Save page source or interact as needed
html = driver.page_source
with open("shohei_ohtani.html", "w", encoding="utf-8") as f:
    f.write(html)

driver.quit()