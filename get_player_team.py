import requests
import json
from bs4 import BeautifulSoup
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
#获取战队和历史战队
def create_session():
    """
    创建一个带有重试机制的session
    """
    session = requests.Session()
    retry = Retry(
        total=3,  # 最多重试3次
        backoff_factor=2,  # 增加重试间隔时间
        status_forcelist=[429, 500, 502, 503, 504]  # 需要重试的HTTP状态码
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_player_data(player_name):
    """
    获取选手的完整数据，包括当前战队和历史战队信息
    Args:
        player_name: 选手ID
    Returns:
        dict: 包含选手信息的字典
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
        # 1. 获取展开后的模板内容
        expand_params = {
            'action': 'expandtemplates',
            'format': 'json',
            'text': f'{{{{PlayerTeamAuto|{player_name}}}}}',
            'prop': 'wikitext'
        }
        
        print("正在获取当前战队信息...")
        response = session.get(api_url, params=expand_params, headers=headers)
        response.raise_for_status()
        team_data = response.json()
        

        # 2. 获取历史战队信息
        history_params = {
            'action': 'expandtemplates',
            'format': 'json',
            'text': f'{{{{THA|{player_name}}}}}',
            'prop': 'wikitext'
        }
        
        response = session.get(api_url, params=history_params, headers=headers)
        response.raise_for_status()
        history_data = response.json()
        
        # 3. 获取完整的HTML内容用于解析
        html_params = {
            'action': 'parse',
            'format': 'json',
            'page': player_name,
            'prop': 'text'
        }
        
        response = session.get(api_url, params=html_params, headers=headers)
        response.raise_for_status()
        html_data = response.json()
        
        if 'error' in html_data:
            print(f"获取HTML内容失败: {html_data['error']}")
            return None
            
        # 解析HTML内容
        soup = BeautifulSoup(html_data['parse']['text']['*'], 'html.parser')
        
        # 保存HTML内容到文件
        with open('player_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("HTML内容已保存到 player_page.html")
        
        # 获取当前战队信息
        current_team = None
        # 在页面中查找包含 "Team:" 的文本
        team_text = soup.find(string=lambda text: text and 'Team:' in text)
        if team_text:
            # 获取包含战队名称的链接
            team_link = team_text.find_next('a')
            if team_link:
                current_team = team_link.get_text(strip=True)
                print(f"找到当前战队: {current_team}")
        
        # 获取历史战队信息
        history_teams = []
        # 首先找到包含 "History" 文本的div
        history_div = soup.find('div', string='History')
        if history_div:
            # 找到包含历史表格的div
            table_div = history_div.find_next('div', class_='infobox-center')
            if table_div:
                # 找到表格
                history_table = table_div.find('table')
                if history_table:
                    # 查找所有包含战队名称的链接
                    team_links = history_table.find_all('a')
                    for link in team_links:
                        team_name = link.get_text(strip=True)
                        if team_name and team_name != '...' and team_name not in history_teams:
                            history_teams.append(team_name)
                    print(f"找到的历史战队: {history_teams}")
                else:
                    print("未找到历史表格")
            else:
                print("未找到包含历史表格的div")
        else:
            print("未找到History文本")
        
        # 打印调试信息
        print("\n=== 展开的当前战队模板 ===")
        print(team_data.get('expandtemplates', {}).get('wikitext', 'No data'))
        
        print("\n=== 展开的历史战队模板 ===")
        print(history_data.get('expandtemplates', {}).get('wikitext', 'No data'))
        
        return {
            'current_team': current_team,
            'history_teams': history_teams,
            'expanded_team_template': team_data.get('expandtemplates', {}).get('wikitext', ''),
            'expanded_history_template': history_data.get('expandtemplates', {}).get('wikitext', '')
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    # 测试选手ID
    player_name = "emo"
    
    # 获取选手数据
    player_data = get_player_data(player_name)
    
    if player_data:
        print("\n=== 解析结果 ===")
        print(f"当前战队: {player_data['current_team']}")
        print("\n历史战队:")
        for team in player_data['history_teams']:
            print(f"- {team}")
    else:
        print(f"无法获取选手 {player_name} 的数据") 