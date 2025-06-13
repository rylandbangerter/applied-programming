import requests
from bs4 import BeautifulSoup

def get_player_id(first_name, last_name):
    # Format the search URL for Baseball Reference
    search_url = f"https://www.baseball-reference.com/search/search.fcgi?search={first_name}+{last_name}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Try to find the first player link in the search results
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/players/') and href.endswith('.shtml'):
            # Player ID is the last part of the URL before .shtml
            player_id = href.split('/')[-1].replace('.shtml', '')
            return player_id
    return None

if __name__ == "__main__":
    first = input("Enter player's first name: ").strip()
    last = input("Enter player's last name: ").strip()
    player_id = get_player_id(first, last)
    if player_id:
        print(f"Player ID for {first} {last}: {player_id}")
    else:
        print("Player not found.")