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

def search_player(player_name, driver):
    # Build the search URL
    search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={player_name.replace(' ', '+')}"
    driver.get(search_url)

    time.sleep(5)  # Wait for page to load

    # Just return the current URL after search
    if (driver.current_url != search_url):
        return driver.current_url
    
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
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    combined_text = []

    # Add main player page content
    main_text = "\n".join(soup.stripped_strings)
    combined_text.append(f"==== Main Player Page ====\n{main_text}\n")

    # Find all year/game log links like /players/gl.fcgi?id= and contain '&t=b&year='
    year_links = soup.select("a[href^='/players/gl.fcgi?id='][href*='&t=b&year=']")
    print("Year links found:", [a.get("href") for a in year_links])
    visited = set()
    for a in year_links:
        href = a.get("href")
        if href and href not in visited:
            visited.add(href)
            full_url = "https://www.baseball-reference.com" + href
            driver.get(full_url)
            time.sleep(5)  # Wait for page to load

            try:
                wait = WebDriverWait(driver, 10)
                # 1. Click the "Share & Export" menu to reveal the dropdown
                share_export_menu = wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//span[text()='Share & Export']")
                    )
                )
                share_export_menu.click()
                time.sleep(1)  # Give time for the dropdown to appear

                # 2. Now look for the CSV button in the revealed dropdown
                csv_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@class='tooltip' and contains(@tip, 'comma-separated values')]")
                    )
                )
                # Scroll the CSV button into view
                driver.execute_script("arguments[0].scrollIntoView(true);", csv_button)
                time.sleep(1)  # Add a delay to allow scrolling to finish

                # Scroll up to avoid sticky headers
                driver.execute_script("window.scrollBy(0, -600);")  # Adjust as needed
                time.sleep(1)  # Add a delay to allow the page to settle

                # Now try clicking the button
                try:
                    csv_button.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", csv_button)
                time.sleep(2)  # Optional: allow time for any download or UI update
                print(f"Clicked CSV button for {a.text.strip()}")
                time.sleep(2)
            except Exception as e:
                print(f"No CSV button found or could not click for {a.text.strip()}: {e}")
                driver.save_screenshot("debug_click_error.png")

            # Parse the table and save as CSV
            year_soup = BeautifulSoup(driver.page_source, "html.parser")
            label = a.text.strip().replace(" ", "_")
            csv_filename = f"{player_name.replace(' ', '_')}_{label}.csv"
            table_to_csv(year_soup, csv_filename)

    # Combine all text into a single string
    return "\n".join(combined_text)

def main():
    service = Service("C:/WebDriver/chromedriver.exe")
    driver = webdriver.Chrome(service=service)

    player_name = input("Enter the player's name: ").strip()
    print(f"Searching for {player_name}...")
    player_url = search_player(player_name, driver)
    if not player_url:
        print("Player not found.")
        driver.quit()
        return

    # # Ask user to confirm the found player page
    # print(f"Found player page: {player_url}")
    # confirm = input("Is this the correct player? (y/n): ").strip().lower()
    # if confirm != "y":
    #     print("Aborting. Please try searching with a different name.")
    #     driver.quit()
    #     return

    print("Scraping data and year links...")
    scrape_player_page_and_years(player_url, driver, player_name)
    driver.quit()

if __name__ == "__main__":
    main()