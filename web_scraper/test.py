# Example (requires selenium and a webdriver)
from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://www.baseball-reference.com/search/search.fcgi?search=Shohei+Ohtani")
print(driver.page_source)
driver.quit()