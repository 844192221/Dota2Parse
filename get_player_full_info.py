import requests
import json
from bs4 import BeautifulSoup
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import re
import os
from urllib.parse import unquote
import random
import sys
import pickle
from pathlib import Path

# 缓存相关配置
CACHE_DIR = "cache"
WIKITEXT_CACHE_FILE = os.path.join(CACHE_DIR, "wikitext_cache.pkl")
HTML_CACHE_FILE = os.path.join(CACHE_DIR, "html_cache.pkl")
TI_CACHE_FILE = os.path.join(CACHE_DIR, "ti_cache.pkl")

def load_cache(cache_file):
    """加载缓存"""
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache_file, cache_data):
    """保存缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump(cache_data, f)

# 加载缓存
wikitext_cache = load_cache(WIKITEXT_CACHE_FILE)
html_cache = load_cache(HTML_CACHE_FILE)
ti_cache = load_cache(TI_CACHE_FILE)

def create_session():
    """
    创建一个带有重试机制的session
    """
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_player_full_info(player_name):
    """
    获取选手的完整信息
    Args:
        player_name: 选手ID
    Returns:
        dict: 包含选手完整信息的字典
    """
    # API配置
    api_url = 'https://liquipedia.net/dota2/api.php'
    headers = {
        'User-Agent': 'Dota2PlayerInfoBot/1.0 (https://github.com/844192221/Dota2Parse; starzhangxing@live.com)',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://liquipedia.net/dota2/',
        'Origin': 'https://liquipedia.net',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'DNT': '1'
    }
    
    # 创建session
    session = create_session()
    
    try:
        # 1. 获取wikitext内容（使用缓存）
        if player_name in wikitext_cache:
            print("使用缓存的wikitext内容")
            wikitext_data = wikitext_cache[player_name]
        else:
            print("从API获取wikitext内容")
            wikitext_params = {
                'action': 'query',
                'format': 'json',
                'titles': player_name,
                'prop': 'revisions',
                'rvprop': 'content'
            }
            
            start_time = time.time()
            retry_count = 0
            while True:
                try:
                    response = session.get(api_url, params=wikitext_params, headers=headers)
                    response.raise_for_status()
                    wikitext_data = response.json()
                    # 保存到缓存
                    wikitext_cache[player_name] = wikitext_data
                    save_cache(WIKITEXT_CACHE_FILE, wikitext_cache)
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        retry_count += 1
                        wait_time = 3600  # 1小时
                        print(f"\n遇到请求限制，第{retry_count}次自动重试...")
                        print(f"将在{wait_time/60:.0f}分钟后自动重试")
                        time.sleep(wait_time)
                        continue
                    raise
                except Exception as e:
                    print(f"Error: {str(e)}")
                    return None
            
            # 严格遵守API限制：每2秒最多1个请求
            time.sleep(2)
        
        # 获取wikitext内容
        pages = wikitext_data['query']['pages']
        page_id = list(pages.keys())[0]
        
        if page_id == '-1':
            print(f"未找到选手 {player_name} 的页面")
            return None
            
        wikitext = pages[page_id]['revisions'][0]['*']
        
        # 2. 获取HTML内容（使用缓存）
        if player_name in html_cache:
            print("使用缓存的HTML内容")
            html_data = html_cache[player_name]
        else:
            print("从API获取HTML内容")
            html_params = {
                'action': 'parse',
                'format': 'json',
                'page': player_name,
                'prop': 'text'
            }
            
            start_time = time.time()
            retry_count = 0
            while True:
                try:
                    response = session.get(api_url, params=html_params, headers=headers)
                    response.raise_for_status()
                    html_data = response.json()
                    # 保存到缓存
                    html_cache[player_name] = html_data
                    save_cache(HTML_CACHE_FILE, html_cache)
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        retry_count += 1
                        wait_time = 3600  # 1小时
                        print(f"\n遇到请求限制，第{retry_count}次自动重试...")
                        print(f"将在{wait_time/60:.0f}分钟后自动重试")
                        time.sleep(wait_time)
                        continue
                    raise
                except Exception as e:
                    print(f"Error: {str(e)}")
                    return None
            
            # 严格遵守API限制：parse请求每30秒最多1个
            time.sleep(30)
        
        if 'error' in html_data:
            print(f"获取HTML内容失败: {html_data['error']}")
            return None
            
        # 解析HTML内容
        soup = BeautifulSoup(html_data['parse']['text']['*'], 'html.parser')
        
        # 3. 获取TI数据（使用缓存）
        if player_name in ti_cache:
            print("使用缓存的TI数据")
            ti_data = ti_cache[player_name]
        else:
            print("从API获取TI数据")
            ti_data = get_ti_stats(player_name, session, api_url, headers)
            if ti_data:
                # 保存到缓存
                ti_cache[player_name] = ti_data
                save_cache(TI_CACHE_FILE, ti_cache)
        
        if ti_data:
            player_info = {
                'id': player_name,
                'name': '',
                'nationality': '',
                'age': '',
                'current_team': '',
                'signature_heroes': [],
                'role': [],
                'history_teams': [],
                'ti_participations': ti_data['total_participations'],
                'ti_best_placement': ti_data['best_placement'],
                'status': ''
            }
        else:
            print(f"无法获取选手 {player_name} 的TI数据")
            return None
        
        # 提取基本信息
        # 从wikitext中提取信息
        # 提取姓名
        name_match = re.search(r'\|\s*name\s*=\s*(.*?)(?:\n|\|)', wikitext)
        if name_match:
            player_info['name'] = name_match.group(1).strip()
            
        # 提取国籍
        country_match = re.search(r'\|\s*country\s*=\s*(.*?)(?:\n|\|)', wikitext)
        if country_match:
            player_info['nationality'] = country_match.group(1).strip()
            
        # 提取出生日期
        birth_patterns = [
            r'\|\s*birth\s*=\s*(.*?)(?:\n|\|)',  # 标准格式
            r'\|\s*birthdate\s*=\s*(.*?)(?:\n|\|)',  # birthdate格式
            r'\|\s*birth_date\s*=\s*(.*?)(?:\n|\|)',  # birth_date格式
            r'\|\s*born\s*=\s*(.*?)(?:\n|\|)'  # born格式
        ]
        
        birth_date = None
        for pattern in birth_patterns:
            birth_match = re.search(pattern, wikitext)
            if birth_match:
                birth_date = birth_match.group(1).strip()
                break
                
        if birth_date:
            try:
                # 处理可能的日期格式
                if '-' in birth_date:
                    birth = datetime.strptime(birth_date, '%Y-%m-%d')
                else:
                    # 如果只有年份，使用1月1日
                    birth = datetime.strptime(f"{birth_date}-01-01", '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                player_info['age'] = str(age)
            except Exception as e:
                player_info['age'] = ''
        
        # 提取位置
        role_patterns = [
            r'\|\s*role\s*=\s*(.*?)(?:\n|\|)',  # 匹配 role=
            r'\|\s*role2\s*=\s*(.*?)(?:\n|\|)', # 匹配 role2=
            r'\|\s*role3\s*=\s*(.*?)(?:\n|\|)'  # 匹配 role3=
        ]
        
        for pattern in role_patterns:
            role_match = re.search(pattern, wikitext)
            if role_match:
                role = role_match.group(1).strip()
                if role and role not in player_info['role']:
                    player_info['role'].append(role)
        
        # 提取擅长英雄
        hero_patterns = [
            r'\|\s*hero\s*=\s*(.*?)(?:\n|\|)',  # 匹配 hero=
            r'\|\s*hero2\s*=\s*(.*?)(?:\n|\|)', # 匹配 hero2=
            r'\|\s*hero3\s*=\s*(.*?)(?:\n|\|)'  # 匹配 hero3=
        ]
        
        for pattern in hero_patterns:
            hero_match = re.search(pattern, wikitext)
            if hero_match:
                hero = hero_match.group(1).strip()
                # 检查英雄名称是否有效（不是空字符串或特殊标记）
                if hero and hero not in ['', '...', 'TBD'] and hero not in player_info['signature_heroes']:
                    player_info['signature_heroes'].append(hero)
                    
        # 提取状态
        status_match = re.search(r'\|\s*status\s*=\s*(.*?)(?:\n|\|)', wikitext)
        if status_match:
            player_info['status'] = status_match.group(1).strip()
            
        # 获取当前战队和历史战队信息
        # 1. 首先尝试从wikitext获取当前战队
        team_text = soup.find(string=lambda text: text and 'Team:' in text)
        if team_text:
            team_link = team_text.find_next('a')
            if team_link:
                player_info['current_team'] = team_link.get_text(strip=True)
        
        # 2. 获取历史战队信息
        # 首先从wikitext中获取
        print("尝试从wikitext获取历史战队...")
        
        # 1. 尝试从Dota 2部分获取
        dota2_section = re.search(r"'''Dota 2''':(.*?)(?='''|$)", wikitext, re.DOTALL)
        if dota2_section:
            print("找到Dota 2部分")
            # 提取所有TH模板中的战队名
            th_matches = re.finditer(r'\{\{TH\|[^|]*\|([^|}]+)', dota2_section.group(1))
            for match in th_matches:
                team = match.group(1).strip()
                if team and team != '...' and team not in player_info['history_teams']:
                    player_info['history_teams'].append(team)
            print(f"从Dota 2部分找到的历史战队: {player_info['history_teams']}")
        
        # 2. 尝试从history字段获取
        print("尝试从history字段获取...")
        history_section = re.search(r'\|\s*history\s*=(.*?)(?:\n\||$)', wikitext, re.DOTALL)
        if history_section:
            print("找到history字段")
            # 提取所有TH模板中的战队名
            th_matches = re.finditer(r'\{\{TH\|[^|]*\|([^|}]+)', history_section.group(1))
            for match in th_matches:
                team = match.group(1).strip()
                if team and team != '...' and team not in player_info['history_teams']:
                    player_info['history_teams'].append(team)
            print(f"从history字段找到的历史战队: {player_info['history_teams']}")
        
        # 3. 从HTML获取历史战队（无论wikitext是否找到战队都尝试）
        print("尝试从HTML获取历史战队...")
        history_div = soup.find('div', string='History')
        if history_div:
            print("找到History div")
            table_div = history_div.find_next('div', class_='infobox-center')
            if table_div:
                print("找到infobox-center div")
                history_table = table_div.find('table')
                if history_table:
                    print("找到历史表格")
                    team_links = history_table.find_all('a')
                    for link in team_links:
                        team_name = link.get_text(strip=True)
                        if team_name and team_name != '...' and team_name not in player_info['history_teams']:
                            player_info['history_teams'].append(team_name)
                    print(f"从HTML中找到的历史战队: {player_info['history_teams']}")
                else:
                    print("未找到历史表格")
            else:
                print("未找到infobox-center div")
        else:
            print("未找到History div")
        
        # 4. 如果历史战队为空，尝试从THA模板获取
        if not player_info['history_teams']:
            print("尝试从THA模板获取历史战队...")
            try:
                history_params = {
                    'action': 'expandtemplates',
                    'format': 'json',
                    'text': f'{{{{THA|{player_name}}}}}',
                    'prop': 'wikitext'
                }
                
                response = session.get(api_url, params=history_params, headers=headers)
                response.raise_for_status()
                history_data = response.json()
                
                # 解析历史战队模板内容
                history_wikitext = history_data.get('expandtemplates', {}).get('wikitext', '')
                if history_wikitext:
                    print("获取到THA模板内容")
                    print(f"THA模板原始内容: {history_wikitext}")
                    
                    # 使用正则表达式提取所有战队
                    # 1. 尝试匹配 team= 格式
                    team_matches = re.finditer(r'team\d*\s*=\s*(.*?)(?:\n|\|)', history_wikitext)
                    for match in team_matches:
                        team = match.group(1).strip()
                        if team and team != '...' and team not in player_info['history_teams']:
                            player_info['history_teams'].append(team)
                    
                    # 2. 尝试匹配 {{TH|...}} 格式
                    if not player_info['history_teams']:
                        print("尝试匹配 {{TH|...}} 格式")
                        th_matches = re.finditer(r'\{\{TH\|[^|]*\|([^|}]+)', history_wikitext)
                        for match in th_matches:
                            team = match.group(1).strip()
                            if team and team != '...' and team not in player_info['history_teams']:
                                player_info['history_teams'].append(team)
                    
                    print(f"从THA模板中找到的历史战队: {player_info['history_teams']}")
                else:
                    print("THA模板内容为空")
            except Exception as e:
                print(f"获取THA模板信息时出错: {str(e)}")
        
        # 等待1秒，遵守API限制
        time.sleep(1)
        
        # 3. 如果当前战队为空，尝试使用PlayerTeamAuto模板获取
        if not player_info['current_team']:
            try:
                # 获取展开后的模板内容
                expand_params = {
                    'action': 'expandtemplates',
                    'format': 'json',
                    'text': f'{{{{PlayerTeamAuto|{player_name}}}}}',
                    'prop': 'wikitext'
                }
                
                response = session.get(api_url, params=expand_params, headers=headers)
                response.raise_for_status()
                team_data = response.json()
                
                # 解析模板内容获取当前战队
                team_wikitext = team_data.get('expandtemplates', {}).get('wikitext', '')
                if team_wikitext:
                    # 尝试从模板内容中提取当前战队
                    team_match = re.search(r'team\s*=\s*(.*?)(?:\n|\|)', team_wikitext)
                    if team_match:
                        current_team = team_match.group(1).strip()
                        if current_team and current_team != '...':
                            player_info['current_team'] = current_team
            except Exception as e:
                print(f"获取当前战队信息时出错: {str(e)}")
        
        return player_info
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    finally:
        session.close()

def get_ti_stats(player_name, session, api_url, headers):
    """
    获取选手的TI参赛数据
    """
    try:
        # 获取Results页面内容
        content_params = {
            'action': 'parse',
            'format': 'json',
            'page': f"{player_name}/Results",
            'prop': 'text'
        }
        
        start_time = time.time()
        retry_count = 0
        while True:
            try:
                response = session.get(api_url, params=content_params, headers=headers)
                response.raise_for_status()
                content_data = response.json()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    retry_count += 1
                    wait_time = 3600  # 1小时
                    print(f"\n遇到请求限制，第{retry_count}次自动重试...")
                    print(f"将在{wait_time/60:.0f}分钟后自动重试")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                print(f"Error getting TI stats: {str(e)}")
                return None
        
        if 'error' in content_data:
            return None
            
        # 获取页面内容
        page_content = content_data['parse']['text']['*']
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # 找到比赛结果表格
        table = soup.find('table', {'class': 'wikitable'})
        if not table:
            return None
        
        # 解析TI参赛情况
        ti_data = {
            'total_participations': 0,
            'best_placement': ''
        }
        
        # 用于记录已经统计过的TI年份
        ti_years = set()
        
        # 遍历表格行
        for row in table.find_all('tr')[1:]:  # 跳过表头
            # 检查是否是高亮行（TI比赛通常会有特殊背景）
            is_highlighted = 'tournament-highlighted-bg' in row.get('class', [])
            
            cols = row.find_all('td')
            if len(cols) < 8:  # 确保有足够的列
                continue
            
            # 获取比赛名称
            tournament_cell = cols[4]
            tournament_link = tournament_cell.find('a')
            if not tournament_link:
                continue
                
            tournament_text = tournament_link.text.strip()
            
            # 使用正则表达式匹配TI正赛（排除预选赛）
            if 'Qualifier' in tournament_text:
                continue
                
            ti_match = re.search(r'The International (\d{4})', tournament_text)
            if not ti_match:
                continue
                
            year = ti_match.group(1)
            
            # 检查是否已经统计过这一年的TI
            if year not in ti_years:
                ti_years.add(year)
                ti_data['total_participations'] += 1
                
                # 获取名次
                placement_cell = cols[1]
                placement = placement_cell.find('b', class_='placement-text')
                if placement:
                    place = placement.text.strip()
                else:
                    place = placement_cell.text.strip()
                
                # 更新最好名次
                if not ti_data['best_placement'] or _is_better_placement(place, ti_data['best_placement']):
                    ti_data['best_placement'] = place
        
        return ti_data
        
    except Exception as e:
        print(f"Error getting TI stats: {str(e)}")
        return None

def _is_better_placement(place1, place2):
    """
    比较两个名次，判断place1是否比place2更好
    """
    def get_numeric_placement(place):
        # 提取数字部分
        match = re.search(r'(\d+)(?:st|nd|rd|th)?', place)
        if match:
            return int(match.group(1))
        return float('inf')
    
    return get_numeric_placement(place1) < get_numeric_placement(place2)

if __name__ == "__main__":
    # 测试模式：只处理几个特定的选手
    TEST_MODE = False
    
    # 创建output文件夹（如果不存在）
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 检查是否存在之前的输出文件，用于获取已处理的选手ID
    existing_files = [f for f in os.listdir(output_dir) if f.startswith("all_players_info_") and f.endswith(".json")]
    processed_ids = set()
    if existing_files:
        # 从最新的文件中读取已处理的选手ID
        latest_file = max(existing_files)
        with open(os.path.join(output_dir, latest_file), 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
            processed_ids = {player['id'] for player in processed_data}
        print(f"从 {latest_file} 中读取了 {len(processed_ids)} 个已处理的选手ID")
    
    # 创建新的输出文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"all_players_info_{timestamp}.json")
    log_file = os.path.join(output_dir, f"empty_history_teams_{timestamp}.log")
    error_log_file = os.path.join(output_dir, f"error_players_{timestamp}.log")
    
    # 读取所有选手ID
    try:
        with open("all_players.txt", "r", encoding="utf-8") as f:
            player_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("错误：找不到 all_players.txt 文件")
        sys.exit(1)
    
    # 过滤掉已经处理过的选手
    player_ids = [pid for pid in player_ids if pid not in processed_ids]
    
    print(f"待处理选手数量: {len(player_ids)}")
    
    # 存储所有选手信息的列表
    all_players_info = []
    
    try:
        # 处理每个选手
        for i, player_id in enumerate(player_ids, 1):
            # URL解码选手ID
            decoded_id = unquote(player_id)
            print(f"\n处理第 {i}/{len(player_ids)} 个选手: {decoded_id}")
            
            # 获取选手完整信息
            player_info = get_player_full_info(decoded_id)
            
            if player_info:
                # 将选手信息添加到列表中
                all_players_info.append(player_info)
                
                # 打印基本信息
                print(f"姓名: {player_info['name']}")
                print(f"国籍: {player_info['nationality']}")
                print(f"当前战队: {player_info['current_team']}")
                print(f"历史战队: {', '.join(player_info['history_teams'])}")
                print(f"TI参赛次数: {player_info['ti_participations']}")
                print(f"TI最好成绩: {player_info['ti_best_placement']}")
                
                # 如果历史战队为空，记录到日志文件
                if not player_info['history_teams']:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"选手ID: {decoded_id}\n")
                        f.write(f"姓名: {player_info['name']}\n")
                        f.write(f"国籍: {player_info['nationality']}\n")
                        f.write(f"当前战队: {player_info['current_team']}\n")
                        f.write(f"TI参赛次数: {player_info['ti_participations']}\n")
                        f.write(f"TI最好成绩: {player_info['ti_best_placement']}\n")
                        f.write("-" * 50 + "\n")
                    print(f"历史战队为空，已记录到日志文件")
                
                # 每处理完一个选手就保存一次JSON文件
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_players_info, f, ensure_ascii=False, indent=4)
                print(f"已保存当前进度到 {output_file}")
            else:
                print(f"无法获取选手 {decoded_id} 的信息")
                # 记录错误到日志文件
                with open(error_log_file, "a", encoding="utf-8") as f:
                    f.write(f"选手ID: {decoded_id}\n")
                    f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-" * 50 + "\n")
                print(f"错误已记录到: {error_log_file}")
                print("程序停止")
                sys.exit(1)
            
            # 添加随机延时（0.5-1秒）避免请求过快
            delay = random.uniform(0.5, 1)
            print(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
        
        print("\n所有选手信息处理完成！")
        print(f"历史战队为空的选手已记录到: {log_file}")
        if os.path.exists(error_log_file):
            print(f"处理失败的选手已记录到: {error_log_file}")
        
    except KeyboardInterrupt:
        print("\n检测到用户中断，保存当前进度...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_players_info, f, ensure_ascii=False, indent=4)
        print(f"进度已保存到 {output_file}")
        sys.exit(0) 