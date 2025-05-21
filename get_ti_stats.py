import requests
import json
import re
from bs4 import BeautifulSoup

def get_ti_stats(player_name):
    """
    获取选手TI参赛次数和最好成绩
    Args:
        player_name: 选手ID
    Returns:
        tuple: (ti_participations, best_placement)
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
            return 0, None
            
        # 获取页面内容
        page_content = content_data['parse']['text']['*']
        
        # 使用BeautifulSoup解析HTML内容
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # 找到比赛结果表格
        table = soup.find('table', {'class': 'wikitable'})
        if not table:
            return 0, None
        
        # 解析TI参赛情况
        ti_participations = 0
        best_placement = float('inf')
        ti_years = set()  # 用于记录已经统计过的TI年份
        
        # 遍历表格行
        for row in table.find_all('tr')[1:]:  # 跳过表头
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
            if ti_match:
                year = ti_match.group(1)
                
                # 检查是否已经统计过这一年的TI
                if year not in ti_years:
                    ti_years.add(year)
                    ti_participations += 1
                    
                    # 获取名次（第2列）
                    placement_cell = cols[1]
                    placement = placement_cell.find('b', class_='placement-text')
                    if placement:
                        place = placement.text.strip()
                    else:
                        place = placement_cell.text.strip()
                    
                    # 提取数字名次
                    placement_match = re.search(r'(\d+)(?:st|nd|rd|th)?', place)
                    if placement_match:
                        placement_num = int(placement_match.group(1))
                        best_placement = min(best_placement, placement_num)
        
        # 如果没有找到TI参赛记录，设置最好名次为None
        if best_placement == float('inf'):
            best_placement = None
            
        return ti_participations, best_placement
        
    except Exception as e:
        return 0, None

if __name__ == "__main__":
    # 测试选手ID
    player_name = "Ame"
    
    # 获取TI数据
    ti_count, best_place = get_ti_stats(player_name)
    
    # 打印结果
    print(f"选手: {player_name}")
    print(f"TI参赛次数: {ti_count}")
    print(f"最好成绩: {best_place}") 