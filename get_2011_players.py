import requests
import json
from bs4 import BeautifulSoup
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session():
    """
    创建一个带有重试机制的session
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_players_by_year(year):
    """
    获取指定年份的选手信息
    Args:
        year: 年份
    Returns:
        list: 包含选手ID的列表
    """
    # API配置
    api_url = 'https://liquipedia.net/dota2/api.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        # 获取统计页面内容
        params = {
            'action': 'parse',
            'format': 'json',
            'page': f'Portal:Statistics/{year}',
            'prop': 'text'
        }
        
        print(f"正在获取{year}年选手信息...")
        response = session.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if 'error' in data:
            print(f"获取{year}年页面内容失败: {data['error']}")
            return []
            
        # 解析HTML内容
        soup = BeautifulSoup(data['parse']['text']['*'], 'html.parser')
        
        # 查找所有选手包装器
        player_wrappers = soup.find_all('div', class_='block-players-wrapper')
        
        if not player_wrappers:
            print(f"未找到{year}年选手信息")
            return []
            
        # 提取选手ID
        players = []
        for wrapper in player_wrappers:
            # 在每个包装器中查找选手链接
            player_link = wrapper.find('a')
            if player_link and player_link.get('href', '').startswith('/dota2/'):
                # 从href中提取选手ID
                player_id = player_link.get('href').split('/dota2/')[-1]
                # 移除可能的_(player)后缀
                player_id = player_id.replace('_(player)', '')
                if player_id and player_id not in players:
                    players.append(player_id)
                    print(f"找到选手: {player_id}")
        
        return players
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
    finally:
        session.close()

def get_all_players():
    """
    获取2011-2025年所有选手信息
    """
    all_players = set()  # 使用集合去重
    
    # 获取2011-2025年的选手
    for year in range(2011, 2026):
        players = get_players_by_year(year)
        all_players.update(players)
        # 添加延迟避免请求过快
        time.sleep(3)
    
    return sorted(list(all_players))  # 转换为排序后的列表

if __name__ == "__main__":
    # 获取所有年份的选手
    all_players = get_all_players()
    
    if all_players:
        # 保存到文件
        with open('all_players.txt', 'w', encoding='utf-8') as f:
            for player in all_players:
                f.write(f"{player}\n")
        
        print(f"\n共找到 {len(all_players)} 名选手")
        print("选手列表已保存到 all_players.txt")
    else:
        print("未找到任何选手信息") 