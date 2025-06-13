import requests
from bs4 import BeautifulSoup
import os

def search_player(player_name):
    search_url = "https://www.baseball-reference.com/search/search.fcgi"
    params = {"search": player_name}
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
    }  
    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching search page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Try to find a direct player summary table link (common for exact matches)
    summary_table = soup.select_one("div.search-item-url a")
    if summary_table and "/players/" in summary_table.get("href", ""):
        return "https://www.baseball-reference.com" + summary_table.get("href")

    # Try to find a "Did you mean" suggestion
    did_you_mean = soup.select_one("div.search-item-name a")
    if did_you_mean and "/players/" in did_you_mean.get("href", ""):
        return "https://www.baseball-reference.com" + did_you_mean.get("href")

    # Try to find a player link in a table (common for popular players)
    table_link = soup.select_one("table.search_results a[href*='/players/']")
    if table_link:
        return "https://www.baseball-reference.com" + table_link.get("href")

    # Fallback: find the first player link anywhere on the page
    for link in soup.find_all("a", href=True):
        if "/players/" in link['href']:
            return "https://www.baseball-reference.com" + link['href']
    return None

def scrape_player_page(player_url):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
    }
    try:
        response = requests.get(player_url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching player page: {e}")
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    texts = soup.stripped_strings
    return "\n".join(texts)


def main():
    player_name = input("Enter the player's name: ").strip()
    print(f"Searching for {player_name}...")
    player_url = search_player(player_name)
    if not player_url:
        print("Player not found.")
        return
    print(f"Found player page: {player_url}")
    print("Scraping data...")
    player_data = scrape_player_page(player_url)
    filename = "".join(c for c in player_name if c.isalnum() or c in (' ', '_')).rstrip()
    filename = filename.replace(" ", "_") + ".txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(player_data)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    main()