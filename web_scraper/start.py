import firebase_admin
from firebase_admin import credentials, firestore
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
from bs4 import BeautifulSoup
import os
import re

def get_firebase_key_path():
    firebase_key_path = os.environ.get("FIREBASE_KEY_PATH")
    if not firebase_key_path:
        raise ValueError("No Firebase key path found. Please set FIREBASE_KEY_PATH in your environment or .env file.")
    return firebase_key_path

def initialize_firebase():
    firebase_key_path = get_firebase_key_path()
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred)
    return firestore.client()

def search_player(player_name, driver):
    # Build the search URL
    search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={player_name.replace(' ', '+')}"
    driver.get(search_url)

    time.sleep(1)  # Wait for page to load

    # Just return the current URL after search
    if (driver.current_url != search_url):
        return driver.current_url
    
    # Try to find a link that matches the player's Baseball-Reference ID pattern
    # (first 2 letters of first name + first 4 letters of last name, case-insensitive)
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
        chars = (last[:4] + first[:2]).lower()  # e.g., "sotoju" for "Juan Soto"
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and chars in href.lower():
                return href
    
    # If no player found, return None
    print(f"No player found for {player_name}")
    return None

def table_to_csv(soup, filename):
    # Find the <pre> tag with the specific id
    pre_tag = soup.find("pre", id="csv_players_standard_batting")
    if not pre_tag:
        print(f"No <pre id='csv_players_standard_batting'> found for {filename}")
        return

    # Get the text content and split into lines
    lines = pre_tag.get_text().strip().splitlines()
    # Remove any lines that are not CSV data (skip lines before ALREADYCSV)
    csv_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("Rk,"):
            csv_start = i
            break
    csv_lines = lines[csv_start:]

    # Write to CSV file
    with open(filename, "w", newline="", encoding="utf-8") as f:
        for line in csv_lines:
            f.write(line + "\n")
    print(f"Saved CSV from <pre> tag: {filename}")

def scrape_player_page_and_years(player_url, driver, player_name):
    driver.get(player_url)
    time.sleep(1)  # Reduced from 5 to 1
    soup = BeautifulSoup(driver.page_source, "html.parser")
    combined_text = []

    # Add main player page content
    main_text = "\n".join(soup.stripped_strings)
    combined_text.append(f"==== Main Player Page ====\n{main_text}\n")

    # Find all year/game log links like /players/gl.fcgi?id= and contain '&t=b&year='
    # Only include links for years 2020-2029 and "post"
    year_links = []
    for a in soup.select("a[href^='/players/gl.fcgi?id='][href*='&t=b']"):
        href = a.get("href", "")
        # Match years 2020-2029 or "Post"
        year_match = re.search(r"&year=(\d{4})", href)
        post_match = re.search(r"&year=0&post=", href)
        if year_match:
            year_val = year_match.group(1)
            if year_val.startswith("202"):
                year_links.append(a)
        elif post_match:
            year_links.append(a)
    print("Year links found:", [a.get("href") for a in year_links])
    visited = set()
    for a in year_links:
        href = a.get("href")
        if href and href not in visited:
            visited.add(href)
            full_url = "https://www.baseball-reference.com" + href
            driver.get(full_url)
            time.sleep(1)  # Reduced from 5 to 1.5

            try:
                # Try to close any pop-ups if present
                close_btn_selectors = [
                    "//div[contains(@class, 'closer')]"
                ]
                for selector in close_btn_selectors:
                    try:
                        close_btn = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        close_btn.click()
                        time.sleep(0.5)
                        print("Closed a pop-up window.")
                        break
                    except Exception:
                        continue
                wait = WebDriverWait(driver, 1)  # Reduced from 10 to 5
                # 1. Wait for the "Share & Export" menu to be visible
                share_export_menu = wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//span[text()='Share & Export']")
                    )
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", share_export_menu
                )
                time.sleep(0.5)  # Reduced from 1 to 0.5

                share_export_menu.click()
                time.sleep(0.5)  # Reduced from 1 to 0.5

                # 2. Now look for the CSV button in the revealed dropdown
                csv_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@class='tooltip' and contains(@tip, 'comma-separated values')]")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", csv_button)
                driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", csv_button)
                time.sleep(0.5)
                print(f"Clicked CSV button for {a.text.strip()}")
            except Exception as e:
                print(f"No CSV button found or could not click for {a.text.strip()}: {e}")
                driver.save_screenshot("debug_click_error.png")
                continue  # Skip to next year

            # Parse the table and save as CSV
            year_soup = BeautifulSoup(driver.page_source, "html.parser")
            pre_tag = year_soup.find("pre", id="csv_players_standard_batting")
            if not pre_tag:
                print(f"No <pre id='csv_players_standard_batting'> found for {csv_filename}")
                continue  # Skip to next year
            label = a.text.strip().replace(" ", "_")
            # Ensure the scraped_files directory exists
            os.makedirs("scraped_files", exist_ok=True)
            csv_filename = os.path.join("scraped_files", f"{player_name.replace(' ', '_')}_{label}.csv")
            table_to_csv(year_soup, csv_filename)

    # Combine all text into a single string
    return "\n".join(combined_text)
def normalize_player_name(name):
        return name.lower().strip()

def main():
    from selenium.webdriver.chrome.options import Options

    service = Service("C:/WebDriver/chromedriver.exe")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    

    player_name = input("Enter the player's name: ")
    player_name = normalize_player_name(player_name)
    
    print(f"Searching for {player_name}...")
    player_url = search_player(player_name, driver)
    if not player_url:
        print("Player not found.")
        driver.quit()
        return

    scrape_player_page_and_years(player_url, driver, player_name)
    driver.quit()

if __name__ == "__main__":
    main()