import requests
from bs4 import BeautifulSoup
import re
import json
import sys
from datetime import datetime


def get_ti_main_event_stats(results_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(results_url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')

    ti_years = []
    ti_pattern = re.compile(r'^The International (20\d{2})\s*$')
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 5:
            tournament = cells[4].get_text(strip=True)
            m = ti_pattern.match(tournament)
            if m:
                ti_years.append(int(m.group(1)))
    ti_participations = len(ti_years)
    ti_best_placement = ""
    if ti_years:
        # 找到这些年份对应的名次
        placements = []
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 5:
                tournament = cells[4].get_text(strip=True)
                m = ti_pattern.match(tournament)
                if m:
                    place = cells[1].get_text(strip=True)
                    match = re.search(r'(\d+)(st|nd|rd|th)?', place)
                    if match:
                        placements.append(int(match.group(1)))
        if placements:
            ti_best_placement = f"{min(placements)}th"
    return ti_participations, ti_best_placement


def parse_age(born_str):
    if not born_str:
        return ""
    # 只取日期部分
    date_match = re.search(r'([A-Za-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}|\d{4})', born_str)
    if not date_match:
        return ""
    date_str = date_match.group(1)
    # 支持多种格式
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%Y"):
        try:
            birth_date = datetime.strptime(date_str, fmt)
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return str(age)
        except Exception:
            continue
    return ""


def get_player_info(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')

    infobox = soup.find('div', class_='fo-nttax-infobox-wrapper')
    if not infobox:
        print('No infobox found!')
        return None

    def get_infobox_value(label):
        tag = infobox.find('div', string=re.compile(f'^{label}:'))
        if tag:
            sibling = tag.find_next_sibling()
            if sibling:
                return sibling.get_text(strip=True)
        return ""

    # id
    player_id = url.rstrip('/').split('/')[-1]
    # name
    name = get_infobox_value("Name")
    # romanized name (可选)
    romanized_name = get_infobox_value("Romanized Name")
    # nationality
    nationality = []
    nat_div = infobox.find('div', string=re.compile('^Nationality:'))
    if nat_div:
        nat_sib = nat_div.find_next_sibling()
        if nat_sib:
            for a in nat_sib.find_all('a'):
                nat = a.get_text(strip=True)
                if nat and nat not in nationality:
                    nationality.append(nat)
    # age
    born = get_infobox_value("Born")
    age = parse_age(born)
    # current team
    current_team = get_infobox_value("Team")
    if not current_team:
        # 有些页面用Current Team，有些用Team
        current_team = get_infobox_value("Current Team")
    # signature heroes
    signature_heroes = []
    sig_div = infobox.find('div', string=re.compile('^Signature Hero'))
    if sig_div:
        sig_sib = sig_div.find_next_sibling()
        if sig_sib:
            for a in sig_sib.find_all('a'):
                hero = a.get('title')
                if hero and hero not in signature_heroes:
                    signature_heroes.append(hero)
            # 有些页面直接是文本
            if not signature_heroes:
                text = sig_sib.get_text(strip=True)
                if text:
                    signature_heroes = [h.strip() for h in text.split(',') if h.strip()]
    # role
    roles = []
    role_div = infobox.find('div', string=re.compile('^Current Role'))
    if role_div:
        role_sib = role_div.find_next_sibling()
        if role_sib:
            for a in role_sib.find_all('a'):
                role = a.get_text(strip=True)
                if role and role not in roles:
                    roles.append(role)
            # 有些页面直接是文本
            if not roles:
                text = role_sib.get_text(strip=True)
                if text:
                    roles = [r.strip() for r in text.split(',') if r.strip()]
    # history teams
    history_teams = []
    # 先找infobox下的History部分
    for section in infobox.find_all('div', class_='infobox-center'):
        for a in section.find_all('a'):
            team = a.get_text(strip=True)
            if team and team not in history_teams:
                history_teams.append(team)
    # ti_participations & ti_best_placement（改为从Results页面获取）
    results_url = url.rstrip('/') + '/Results'
    ti_participations, ti_best_placement = get_ti_main_event_stats(results_url)
    # status
    years_active = get_infobox_value("Years Active")
    status = "Active"
    if years_active:
        if 'Present' not in years_active and not re.search(r'202[3-9]', years_active):
            status = "Inactive"
    # 兼容页面顶部描述
    if soup.find(string=re.compile('inactive', re.I)):
        status = "Inactive"

    player_info = {
        "id": player_id,
        "name": name,
        "romanized_name": romanized_name,
        "nationality": nationality,
        "age": age,
        "current_team": current_team,
        "signature_heroes": signature_heroes,
        "role": roles,
        "history_teams": history_teams,
        "ti_participations": ti_participations,
        "ti_best_placement": ti_best_placement,
        "status": status
    }
    return player_info


def main():
    if len(sys.argv) < 2:
        print("用法: python get_player_info.py <选手id>")
        return
    player_id = sys.argv[1]
    url = f"https://liquipedia.net/dota2/{player_id}"
    info = get_player_info(url)
    if info:
        filename = f"{info['id']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        print(f"已保存到: {filename}")
    else:
        print("未能抓取到选手信息！")

if __name__ == "__main__":
    main() 