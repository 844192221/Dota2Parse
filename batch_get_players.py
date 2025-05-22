import json
import time
import random
import os
from get_player_info import get_player_info

RETRY_DELAY = 60
SLEEP_MIN = 1
SLEEP_MAX = 3
MAX_RETRIES = 5

unfinished_file = 'unfinished_ids.txt'
output_file = 'all_players.json'

# 读取未完成名单优先
if os.path.exists(unfinished_file):
    with open(unfinished_file, 'r', encoding='utf-8') as f:
        player_lines = [line.strip() for line in f if line.strip()]
    print(f'继续处理未完成名单，共{len(player_lines)}人')
else:
    player_lines = []
    with open('player_appearance_count.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if line.count(':') >= 2:
                player_lines.append(line.strip())

all_players = []
failed_ids = []
try:
    for idx, line in enumerate(player_lines):
        # 解析 name, href, count
        try:
            name, href, count = line.split(':', 2)
        except Exception:
            print(f'行格式错误: {line}')
            continue
        url = f'https://liquipedia.net{href}'
        print(f'Processing: {name} ({idx+1}/{len(player_lines)})')
        for attempt in range(MAX_RETRIES):
            try:
                info = get_player_info(url)
                if info:
                    # name字段统一为list
                    names = []
                    if info.get('name'):
                        names.append(info['name'])
                    if info.get('romanized_name') and info['romanized_name'] not in names:
                        names.append(info['romanized_name'])
                    info['name'] = names
                    info.pop('romanized_name', None)
                    all_players.append(info)
                else:
                    failed_ids.append(name)
                break
            except Exception as e:
                print(f'Error processing {name}: {e}')
                if attempt < MAX_RETRIES - 1:
                    print(f'Retrying {name} after {RETRY_DELAY}s... (attempt {attempt+2}/{MAX_RETRIES})')
                    time.sleep(RETRY_DELAY)
                else:
                    failed_ids.append(name)
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
        # 记录未完成名单
        unfinished = player_lines[idx+1:]
        with open(unfinished_file, 'w', encoding='utf-8') as f:
            for u in unfinished:
                f.write(u + '\n')
        if not unfinished:
            os.remove(unfinished_file)
except KeyboardInterrupt:
    print('\n检测到中断，正在保存当前数据...')
finally:
    if all_players:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_players, f, ensure_ascii=False, indent=2)
        print(f'已写入: {output_file}，共{len(all_players)}人')
    # 记录失败名单
    if failed_ids:
        with open('failed_players.txt', 'w', encoding='utf-8') as f:
            for pid in failed_ids:
                f.write(pid + '\n')
    print('批量处理完成！') 