import csv
import os
import re
import random
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def normalize_player_name(name):
    return name.lower().strip()

def table_to_csv(soup, filename):
    pre_tag = soup.find("pre", id="csv_players_standard_batting")
    if not pre_tag:
        print(f"No <pre id='csv_players_standard_batting'> found for {filename}")
        return
    lines = pre_tag.get_text().strip().splitlines()
    csv_start = next((i for i, line in enumerate(lines) if line.strip().startswith("Rk,")), 0)
    csv_lines = lines[csv_start:]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write("\n".join(csv_lines) + "\n")
    print(f"Saved CSV: {filename}")

def get_year_links(soup):
    year_links, seen_hrefs = [], set()
    for a in soup.select("a[href^='/players/gl.fcgi?id='][href*='&t=b']"):
        href = a.get("href", "")
        if href in seen_hrefs:
            continue
        if re.search(r"&year=(202\d)", href) or re.search(r"&year=0&post=", href):
            year_links.append((a, href))
            seen_hrefs.add(href)
    return year_links

def close_popup_if_present(driver):
    try:
        close_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'closer')]"))
        )
        close_btn.click()
        print("Closed a pop-up window.")
    except Exception:
        pass

def click_share_export_and_csv(driver):
    # Scroll until the "Share & Export" element is in view and clickable
    actions = ActionChains(driver)
    actions.move_by_offset(100, 50).perform()
    while True:
        driver.execute_script("window.scrollBy(0, 1000);")
        try:
            print("Attempting to click 'Share & Export'...")
            share_export_menu = driver.find_element(By.XPATH, "//span[text()='Share & Export']")
            # Ensure the element is in view before clicking
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_export_menu)            
            # Click the "Share & Export" menu
            close_popup_if_present(driver)
            share_export_menu.click()
            print("Clicked 'Share & Export' successfully.")
            break  # Exit loop if successful
        except Exception:
            driver.execute_script("window.scrollBy(0, 1000);")  # Scroll down more and try again


    csv_button = driver.find_element(
        By.XPATH, "//button[@class='tooltip' and contains(@tip, 'comma-separated values')]"
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", csv_button)
    # driver.execute_script("window.scrollBy(0, -100);")
    driver.execute_script("arguments[0].click();", csv_button)

def last_name_length(last_name):
    if len(last_name) <=5:
        last_char_count = len(last_name)
    else:
        last_char_count = 5
    return last_char_count

def search_player(player_name, driver):
    search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={player_name.replace(' ', '+')}"
    driver.get(search_url)
    if driver.current_url != search_url:
        return driver.current_url
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
        chars = (last[:last_name_length(last)] + first[:2]).lower()  # e.g., "sotoju" for "Juan Soto"
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and chars in href.lower():
                return href
    print(f"No player found for {player_name}")
    return None

def load_player_page(driver, player_url):
    # Only load the player page if not already there
    if driver.current_url != player_url:
        driver.get(player_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "head")))
    return BeautifulSoup(driver.page_source, "html.parser")

def load_year_page(driver, year_url):
    # Only load the year page if not already there
    if driver.current_url != year_url:
        driver.get(year_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "head")))
    return None

def scrape_player_page_and_years(player_url, driver, player_name):
    soup = load_player_page(driver, player_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    year_links = get_year_links(soup)
    print("Year links found:", [href for _, href in year_links])
    for a, href in year_links:
        full_url = "https://www.baseball-reference.com" + href
        # Only load the year page if not already there
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        load_year_page(driver, full_url)
        try:
            close_popup_if_present(driver)
            click_share_export_and_csv(driver)
            print(f"Clicked CSV button for {a.text.strip()}")
        except Exception as e:
            print(f"No CSV button found or could not click for {a.text.strip()}: {e}")
            continue
        year_soup = BeautifulSoup(driver.page_source, "html.parser")
        pre_tag = year_soup.find("pre", id="csv_players_standard_batting")
        if not pre_tag:
            print(f"No <pre id='csv_players_standard_batting'> found for {player_name}_{a.text.strip()}")
            continue
        label = a.text.strip().replace(" ", "_")
        # os.makedirs("scraped_files", exist_ok=True)
        csv_filename = os.path.join("scraped_files", f"{player_name.replace(' ', '_')}_{label}.csv")
        table_to_csv(year_soup, csv_filename)
        time.sleep(random.uniform(2, 6))  # Wait 2-6 seconds between requests to avoid overwhelming the server

def initialize_driver():
    from selenium.webdriver.chrome.options import Options
    service = Service("C:/WebDriver/chromedriver.exe")
    chrome_options = Options()
    # Add any necessary options here
    chrome_options.add_argument("--start-maximized")  # Start Chrome maximized
    # chrome_options.add_argument("--headless")  # Run Chrome in headless mode for faster loading
    chrome_options.page_load_strategy = 'eager' # Or 'none' for faster loading

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def main():
    os.makedirs("scraped_files", exist_ok=True)
    with open("C:/Users/taylo/OneDrive/Desktop/applied-programming/web_scraper/column2_only.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            driver = initialize_driver()
            if not row:
                continue
            player_name = normalize_player_name(row[0])
            print(f"Searching for {player_name}...")
            player_url = search_player(player_name, driver)
            if not player_url:
                print(f"Player not found: {player_name}")
                continue
            scrape_player_page_and_years(player_url, driver, player_name)
            driver.quit()

if __name__ == "__main__":
    main()