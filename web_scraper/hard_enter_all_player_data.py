import csv
import os
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        close_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'closer')]"))
        )
        close_btn.click()
        print("Closed a pop-up window.")
    except Exception:
        pass

def click_share_export_and_csv(driver):
    wait = WebDriverWait(driver, 10)
    share_export_menu = wait.until(
        EC.visibility_of_element_located((By.XPATH, "//span[text()='Share & Export']"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", share_export_menu)
    share_export_menu.click()
    csv_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='tooltip' and contains(@tip, 'comma-separated values')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", csv_button)
    driver.execute_script("window.scrollBy(0, -100);")
    driver.execute_script("arguments[0].click();", csv_button)

def search_player(player_name, driver):
    search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={player_name.replace(' ', '+')}"
    driver.get(search_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    if driver.current_url != search_url:
        return driver.current_url
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
        chars = (last[:5] + first[:2]).lower()
        links = driver.find_elements(By.TAG_NAME, "a")
        pattern = re.compile(r"/players/[a-z]/([a-z]{5}[a-z]{2}\d{2})\.shtml", re.IGNORECASE)
        for link in links:
            href = link.get_attribute("href")
            if href:
                match = pattern.search(href)
                if match and all(c in match.group(1) for c in chars):
                    return href
    print(f"No player found for {player_name}")
    return None

def scrape_player_page_and_years(player_url, driver, player_name):
    driver.get(player_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    year_links = get_year_links(soup)
    print("Year links found:", [href for _, href in year_links])
    for a, href in year_links:
        full_url = "https://www.baseball-reference.com" + href
        driver.get(full_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
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
        os.makedirs("scraped_files", exist_ok=True)
        csv_filename = os.path.join("scraped_files", f"{player_name.replace(' ', '_')}_{label}.csv")
        table_to_csv(year_soup, csv_filename)

def main():
    from selenium.webdriver.chrome.options import Options
    service = Service("C:/WebDriver/chromedriver.exe")
    chrome_options = Options()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    os.makedirs("scraped_files", exist_ok=True)
    with open("C:/Users/taylo/OneDrive/Desktop/applied-programming/web_scraper/column2_only.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
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