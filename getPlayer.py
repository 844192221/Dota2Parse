import requests
from bs4 import BeautifulSoup
from collections import Counter
import time

def fetch_player_names(year):
    url = f"https://liquipedia.net/dota2/Portal:Statistics/{year}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; scraping for research purpose)"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch {year}: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table', class_='wikitable')

    player_list = []
    for table in tables:
        headers = [th.text.strip().lower() for th in table.find_all('th')]
        if any('player' in h for h in headers) and any('earnings' in h for h in headers):
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    player_cell = next((td for td in cells if td.find('a')), None)
                    if player_cell:
                        a_tag = player_cell.find('a')
                        name = a_tag.get_text(strip=True)
                        href = a_tag['href']
                        if name and href:
                            player_list.append((name, href))
            break  # 假设找到一张就够了

    return player_list

def main():
    year_range = range(2011, 2026)
    player_counter = Counter()
    href_map = {}

    for year in year_range:
        print(f"Fetching {year}...")
        players = fetch_player_names(year)
        for name, href in players:
            key = f"{name}:{href}"
            player_counter[key] += 1
            href_map[key] = (name, href)
        time.sleep(1)  # 防止请求过快被ban

    print("\n--- Player Appearance Count (2011-2025) ---")
    for key, count in player_counter.most_common():
        name, href = href_map[key]
        print(f"{name}:{href}:{count}")

    # 保存为文件
    with open("player_appearance_count.txt", "w", encoding="utf-8") as f:
        for key, count in player_counter.most_common():
            name, href = href_map[key]
            f.write(f"{name}:{href}:{count}\n")

if __name__ == "__main__":
    main()