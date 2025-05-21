import requests
import json
import re
from bs4 import BeautifulSoup
# 获取选手ti次数  ti最好成绩
def get_detailed_ti_stats(player_name):
    """
    获取选手详细的TI参赛数据
    Args:
        player_name: 选手ID
    Returns:
        dict: 包含TI参赛详细信息的字典
    """
    # API配置
    api_url = 'https://liquipedia.net/dota2/api.php'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 获取Results页面内容
    content_params = {
        'action': 'parse',
        'format': 'json',
        'page': f"{player_name}/Results",
        'prop': 'text'
    }
    
    try:
        # 发送API请求
        response = requests.get(api_url, params=content_params, headers=headers)
        response.raise_for_status()
        content_data = response.json()
        
        if 'error' in content_data:
            return None
            
        # 获取页面内容
        page_content = content_data['parse']['text']['*']
        
        # 使用BeautifulSoup解析HTML内容
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # 找到比赛结果表格
        table = soup.find('table', {'class': 'wikitable'})
        if not table:
            return None
        
        # 解析TI参赛情况
        ti_data = {
            'total_participations': 0,
            'years': [],
            'details': [],
            'best_placement': {
                'year': '',
                'place': '',
                'prize': ''
            }
        }
        
        # 遍历表格行
        for row in table.find_all('tr')[1:]:  # 跳过表头
            # 检查是否是高亮行（TI比赛通常会有特殊背景）
            is_highlighted = 'tournament-highlighted-bg' in row.get('class', [])
            
            cols = row.find_all('td')
            if len(cols) < 8:  # 确保有足够的列
                continue
            
            # 获取比赛名称
            tournament_cell = cols[4]  # 第5列包含比赛名称
            tournament_link = tournament_cell.find('a')
            if not tournament_link:
                continue
                
            tournament_text = tournament_link.text.strip()
            
            # 使用正则表达式匹配TI正赛
            ti_match = re.search(r'The International (\d{4})(?!.*Qualifier)', tournament_text)
            if not ti_match:
                continue
                
            year = ti_match.group(1)
            
            # 获取日期（第1列）
            date = cols[0].text.strip()
            
            # 获取名次（第2列）
            placement_cell = cols[1]
            placement = placement_cell.find('b', class_='placement-text')
            if placement:
                place = placement.text.strip()
            else:
                place = placement_cell.text.strip()
            
            # 获取队伍名称（第6列）
            team_cell = cols[5]
            team = team_cell.text.strip()
            
            # 获取奖金（第8列）
            prize = cols[7].text.strip() if len(cols) > 7 else ''
            
            if year not in ti_data['years']:
                ti_data['years'].append(year)
                ti_data['total_participations'] += 1
                
                # 记录详细信息
                detail = {
                    'year': year,
                    'date': date,
                    'place': place,
                    'team': team,
                    'prize': prize,
                    'is_highlighted': is_highlighted
                }
                ti_data['details'].append(detail)
                
                # 更新最好名次
                if not ti_data['best_placement']['year'] or _is_better_placement(place, ti_data['best_placement']['place']):
                    ti_data['best_placement'] = {
                        'year': year,
                        'place': place,
                        'prize': prize
                    }
        
        # 按年份排序
        ti_data['years'].sort()
        ti_data['details'].sort(key=lambda x: x['year'])
        
        return ti_data
        
    except Exception as e:
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
    # 测试选手ID
    player_name = "AhJit"
    
    # 获取详细TI数据
    ti_data = get_detailed_ti_stats(player_name)
    
    if ti_data:
        print(f"\n选手: {player_name}")
        print(f"TI参赛次数: {ti_data['total_participations']}")
        print(f"TI参赛年份: {', '.join(ti_data['years'])}")
        print(f"\n最好成绩:")
        print(f"年份: {ti_data['best_placement']['year']}")
        print(f"名次: {ti_data['best_placement']['place']}")
        print(f"奖金: {ti_data['best_placement']['prize']}")
        
        print("\n详细参赛记录:")
        for detail in ti_data['details']:
            print(f"\nTI{detail['year']}:")
            print(f"日期: {detail['date']}")
            print(f"名次: {detail['place']}")
            print(f"队伍: {detail['team']}")
            print(f"奖金: {detail['prize']}")
    else:
        print(f"无法获取选手 {player_name} 的数据") 