import requests
import json
from bs4 import BeautifulSoup
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
#获取的信息
#id id里获取
#name由givenname familyname组成
#age 用当前日期减去出生日期
#nationality 从country里获取
#status 从status里获取
#role 从role里获取
#擅长英雄从 hero hero2 hero3里获取
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

def get_player_wikitext(player_name):
    """
    获取选手页面的wikitext
    Args:
        player_name: 选手ID
    Returns:
        str: 页面的wikitext内容
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
        # 获取页面wikitext
        params = {
            'action': 'query',
            'format': 'json',
            'titles': player_name,
            'prop': 'revisions',
            'rvprop': 'content'
        }
        
        print(f"正在获取 {player_name} 的wikitext...")
        response = session.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # 获取页面内容
        pages = data['query']['pages']
        page_id = list(pages.keys())[0]
        
        if page_id == '-1':
            print(f"未找到选手 {player_name} 的页面")
            return None
            
        # 获取wikitext内容
        wikitext = pages[page_id]['revisions'][0]['*']
        
        # 保存到文件
        with open(f'{player_name}_wikitext.txt', 'w', encoding='utf-8') as f:
            f.write(wikitext)
        print(f"wikitext已保存到 {player_name}_wikitext.txt")
        
        return wikitext
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    # 获取Ame的wikitext
    player_name = "emo"
    wikitext = get_player_wikitext(player_name)
    
    if wikitext:
        print("\n=== Wikitext内容 ===")
        print(wikitext)
    else:
        print(f"无法获取选手 {player_name} 的wikitext") 