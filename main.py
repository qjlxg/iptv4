import requests
import csv
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 定义要抓取的m3u直播源链接列表
m3u_urls = [
'https://github.com/hujingguang/ChinaIPTV/raw/main/cnTV_AutoUpdate.m3u8',
'https://github.com/LITUATUI/M3UPT/raw/main/M3U/M3UPT.m3u',
'https://github.com/Daopanhya/IPTV/raw/main/%E0%BA%8A%E0%BB%88%E0%BA%AD%E0%BA%87%E0%BA%81%E0%BA%B4%E0%BA%A5%E0%BA%B2.m3u',
'https://github.com/naveenland4/News_Channels/raw/main/news_channels.m3u',
'https://github.com/fenxp/iptv/raw/main/live/ipv6.m3u',
'https://raw.githubusercontent.com/drangjchen/IPTV/main/M3U/ipv6.m3u',
'https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u',
'https://raw.githubusercontent.com/balala2oo8/iptv/main/o.m3u',
'https://raw.githubusercontent.com/ssili126/tv/main/itvlist.m3u',
'https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u',
'https://github.com/tangbojin/update_iptv/raw/main/src/main/resources/my_tv.m3u',
'https://github.com/FunctionError/PiratesTv/raw/main/combined_playlist.m3u',
'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u',
'https://github.com/qjlxg/TVIP/raw/Files/CCTV.m3u',
'https://github.com/qjlxg/TVIP/raw/Files/CNTV.m3u',
'https://github.com/qjlxg/TVIP/raw/Files/IPTV.m3u',
'https://github.com/qjlxg/TVIP/raw/Files/ru.m3u',
'https://github.com/qjlxg/TVIP/raw/Files/un.m3u',
'https://github.com/qjlxg/MyTV/raw/main/TW_switch.m3u',
'https://github.com/qjlxg/IPTVzb1/raw/main/%E7%BB%93%E6%9E%9C.m3u',
'https://github.com/qjlxg/IPTVzb1/raw/main/%E9%85%92%E5%BA%97%E6%BA%90.m3u',
'https://github.com/osgioia/iptv_generator/raw/main/plex.m3u',
'https://github.com/Jason6111/iptv/raw/main/m3u/IPTV.m3u',
'https://github.com/Jason6111/iptv/raw/main/m3u/aptv.m3u',
'https://github.com/Jason6111/iptv/raw/main/m3u/aptv4.m3u',
'https://github.com/Jason6111/iptv/raw/main/m3u/CNTV.m3u',
'https://github.com/Jason6111/iptv/raw/main/m3u/CCTV.m3u'
 
]

# 准备写入CSV文件的字段名
fieldnames = ['tvg-name', 'tvg-id', 'tvg-logo', 'group-title', 'link']

# 初始化CSV写入器
csv_filename = 'live_streams.csv'

def process_playlist(m3u_url):
    try:
        print(f"Processing {m3u_url}...")
        response = requests.get(m3u_url, timeout=5)
        if response.status_code == 200:
            playlist_content = response.text

            # 使用正则表达式解析每条直播流信息
            pattern = r'#EXTINF:-1(?: tvg-id="(.*?)")?(?: tvg-name="(.*?)")?(?: tvg-logo="(.*?)")?(?: group-title="(.*?)")?,\s*(.*?)\n(https?://[^\s]+)'
            matches = re.findall(pattern, playlist_content, re.DOTALL | re.MULTILINE)

            streams = []

            # 处理匹配结果
            for match in matches:
                tvg_id = match[0] if match[0] else match[1]  # 如果tvg-id为空，则使用tvg-name作为tvg-id
                tvg_name = match[1] if match[1] else ''
                tvg_logo = match[2] if match[2] else ''
                group_title = match[3] if match[3] else ''
                stream_link = match[5].strip()

                # 过滤掉包含.php的链接
                if '.php' in stream_link:
                    continue

                # 修改 group-title 标签
                if group_title in ['内蒙频道', '浙江频道', '上海频道', '地方','广东频道']:
                    group_title = '地方频道'
                elif group_title == 'NewTv':
                    group_title = '数字频道'
                elif '卫视' in group_title:
                    group_title = '卫视频道'
                elif group_title == '数字':
                    group_title = '数字频道'
                elif group_title == '央视':
                    group_title = '央视频道'
                elif group_title == 'NewTV频道':
                    group_title = '数字频道'                    
                elif group_title == '动画频道':
                    group_title = '少儿频道' 
                elif group_title == '港澳台频道':
                    group_title = '港·澳·台'
                  
                # 修改 tvg-name 标签
                tvg_name = re.sub(r'newtv', 'NewTv', tvg_name, flags=re.IGNORECASE)
                if tvg_name == 'CCTV5PLUS':
                    tvg_name = 'CCTV5+'

                # 根据特定条件删除直播源
                if re.search(r'更新日期|日期|请阅读|yuanzl77.github.io|^$', tvg_name, re.IGNORECASE) or group_title == '公告':
                    continue  # 跳过符合条件的直播源

                streams.append({
                    'tvg-name': tvg_name,
                    'tvg-id': tvg_id,
                    'tvg-logo': tvg_logo,
                    'group-title': group_title,
                    'link': stream_link
                })

            return streams
        else:
            print(f"Failed to fetch playlist from {m3u_url}. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception while fetching {m3u_url}: {str(e)}")
        return []

# 使用线程池进行并发请求和处理
with ThreadPoolExecutor(max_workers=5) as executor, open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    futures = [executor.submit(process_playlist, url) for url in m3u_urls]
    
    seen_links = set()  # 用于存放已经写入的直播源链接，用于去重

    for future in tqdm(as_completed(futures), total=len(futures), desc="Processing playlists"):
        streams = future.result()
        for stream in streams:
            # 去重处理
            if stream['link'] not in seen_links:
                seen_links.add(stream['link'])
                # 写入CSV文件
                writer.writerow(stream)

print(f"CSV文件 '{csv_filename}' 生成成功。")
