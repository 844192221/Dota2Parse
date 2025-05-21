import requests
import json
import re
from bs4 import BeautifulSoup
#ti详细数据
class Dota2PlayerData:
    def __init__(self):
        self.api_url = 'https://liquipedia.net/dota2/api.php'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_player_results(self, player_name):
        """
        获取选手比赛结果数据
        """
        # 创建日志文件
        log_file = f"{player_name}_debug.log"
        raw_content_file = f"{player_name}_results.html"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"\n正在获取选手 {player_name} 的数据...\n")
            
            # 获取Results页面内容
            content_params = {
                'action': 'parse',
                'format': 'json',
                'page': f"{player_name}/Results",  # 直接访问Results页面
                'prop': 'text'
            }
            
            f.write("\nAPI请求参数:\n")
            f.write(json.dumps(content_params, indent=2))
            
            try:
                response = requests.get(self.api_url, params=content_params, headers=self.headers)
                response.raise_for_status()
                content_data = response.json()
                
                if 'error' in content_data:
                    f.write(f"\nAPI错误: {content_data['error']}\n")
                    return None
                
                if 'parse' not in content_data:
                    f.write("\nAPI响应中没有parse字段\n")
                    return None
                    
                # 获取页面内容
                page_content = content_data['parse']['text']['*']
                
                # 保存完整的页面内容到文件
                with open(raw_content_file, 'w', encoding='utf-8') as content_file:
                    content_file.write(page_content)
                f.write(f"\n完整页面内容已保存到 {raw_content_file}\n")
                
                # 使用BeautifulSoup解析HTML内容
                soup = BeautifulSoup(page_content, 'html.parser')
                
                # 找到比赛结果表格
                table = soup.find('table', {'class': 'wikitable'})
                if not table:
                    f.write("\n未找到比赛结果表格\n")
                    return None
                    
                f.write("\n找到比赛结果表格\n")
                
                # 解析TI参赛情况
                ti_participation = self._parse_ti_participation(table)
                
                # 打印解析后的数据
                f.write("\nTI参赛情况:\n")
                f.write(json.dumps(ti_participation, indent=2, ensure_ascii=False))
                
                return ti_participation
                
            except Exception as e:
                f.write(f"\nError fetching results for {player_name}: {str(e)}\n")
                return None

    def get_player_info(self, player_name):
        """
        获取选手基本信息
        """
        print(f"\n正在获取选手 {player_name} 的基本信息...")
        
        # 获取选手页面内容
        content_params = {
            'action': 'parse',
            'format': 'json',
            'page': player_name,  # 直接访问选手页面
            'prop': 'text'
        }
        
        print("\nAPI请求参数:")
        print(json.dumps(content_params, indent=2))
        
        try:
            response = requests.get(self.api_url, params=content_params, headers=self.headers)
            response.raise_for_status()
            content_data = response.json()
            
            if 'error' in content_data:
                print(f"API错误: {content_data['error']}")
                return None
                
            # 获取页面内容
            page_content = content_data['parse']['text']['*']
            
            # 使用BeautifulSoup解析HTML内容
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # 找到选手信息表格
            info_table = soup.find('table', {'class': 'infobox'})
            if not info_table:
                print("\n未找到选手信息表格")
                return None
                
            # 解析选手信息
            player_info = self._parse_player_info(info_table)
            
            # 打印解析后的数据
            print("\n选手信息:")
            print(json.dumps(player_info, indent=2, ensure_ascii=False))
            
            return player_info
            
        except Exception as e:
            print(f"Error fetching player info for {player_name}: {str(e)}")
            return None

    def _parse_player_info(self, table):
        """
        解析选手基本信息
        """
        player_info = {
            'name': '',
            'romanized_name': '',
            'nationality': '',
            'birth_date': '',
            'age': '',
            'region': '',
            'years_active': '',
            'current_role': '',
            'current_team': '',
            'alternate_ids': [],
            'total_winnings': '',
            'signature_heroes': []
        }
        
        # 遍历表格行
        for row in table.find_all('tr'):
            # 获取标题和内容
            header = row.find('th')
            content = row.find('td')
            
            if not header or not content:
                continue
                
            header_text = header.get_text(strip=True)
            content_text = content.get_text(strip=True)
            
            # 根据标题填充信息
            if 'Name' in header_text:
                player_info['name'] = content_text
            elif 'Romanized Name' in header_text:
                player_info['romanized_name'] = content_text
            elif 'Nationality' in header_text:
                player_info['nationality'] = content_text
            elif 'Birth Date' in header_text:
                player_info['birth_date'] = content_text
            elif 'Age' in header_text:
                player_info['age'] = content_text
            elif 'Region' in header_text:
                player_info['region'] = content_text
            elif 'Years Active' in header_text:
                player_info['years_active'] = content_text
            elif 'Current Role' in header_text:
                player_info['current_role'] = content_text
            elif 'Current Team' in header_text:
                player_info['current_team'] = content_text
            elif 'Alternate IDs' in header_text:
                player_info['alternate_ids'] = [id.strip() for id in content_text.split(',')]
            elif 'Total Winnings' in header_text:
                player_info['total_winnings'] = content_text
            elif 'Signature Heroes' in header_text:
                player_info['signature_heroes'] = [hero.strip() for hero in content_text.split(',')]
        
        return player_info

    def _parse_ti_participation(self, table):
        """
        解析TI参赛情况
        """
        ti_participation = {
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
            
            if year not in ti_participation['years']:
                ti_participation['years'].append(year)
                ti_participation['total_participations'] += 1
                
                # 记录详细信息
                detail = {
                    'year': year,
                    'date': date,
                    'place': place,
                    'team': team,
                    'prize': prize,
                    'is_highlighted': is_highlighted
                }
                ti_participation['details'].append(detail)
                
                # 更新最好名次
                if not ti_participation['best_placement']['year'] or self._is_better_placement(place, ti_participation['best_placement']['place']):
                    ti_participation['best_placement'] = {
                        'year': year,
                        'place': place,
                        'prize': prize
                    }
        
        # 按年份排序
        ti_participation['years'].sort()
        ti_participation['details'].sort(key=lambda x: x['year'])
        
        return ti_participation

    def _is_better_placement(self, place1, place2):
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

# Example usage:
if __name__ == "__main__":
    # 创建实例
    dota2_data = Dota2PlayerData()
    
    # 测试获取选手数据
    player_name = "Arteezy"
    results = dota2_data.get_player_results(player_name)
    info = dota2_data.get_player_info(player_name)
    
    if results:
        print("\nTI参赛情况:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    if info:
        print("\n选手信息:")
        print(json.dumps(info, indent=2, ensure_ascii=False)) 