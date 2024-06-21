import csv
import cv2
import requests
from tqdm import tqdm
from datetime import datetime
import concurrent.futures

csv_filename = 'live_streams.csv'
output_m3u_filename = 'iptv4.m3u'
output_txt_filename = 'iptv4.txt'
moban_filename = 'moban.txt'

def test_stream_availability(stream_link):
    try:
        cap = cv2.VideoCapture(stream_link)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return ret
        return False
    except Exception as e:
        print(f"Exception while testing stream {stream_link}: {str(e)}")
        return False

def test_stream_speed(stream_link):
    try:
        start_time = datetime.now()
        response = requests.get(stream_link, stream=True, timeout=5)
        if response.status_code == 200:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            return duration
        return float('inf')
    except Exception as e:
        print(f"Exception while testing speed for stream {stream_link}: {str(e)}")
        return float('inf')

def read_moban_file(moban_filename):
    with open(moban_filename, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file]

def read_and_deduplicate_csv(csv_filename):
    unique_streams = {}
    with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            link = row['link']
            if link not in unique_streams:
                unique_streams[link] = row
    return list(unique_streams.values())

def validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename):
    valid_streams = []
    channel_order = read_moban_file(moban_filename)
    unique_streams = read_and_deduplicate_csv(csv_filename)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(test_stream_availability, row['link']): row for row in unique_streams}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Validating streams"):
            row = futures[future]
            try:
                if future.result():
                    valid_streams.append(row)
                else:
                    print(f"直播源 {row['link']} 不可用，将被忽略。")
            except Exception as e:
                print(f"直播源 {row['link']} 检测时出现异常：{e}")

    valid_streams = [stream for stream in valid_streams if stream['tvg-name'] and stream['link']]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        speed_futures = {executor.submit(test_stream_speed, stream['link']): stream for stream in valid_streams}
        for future in tqdm(concurrent.futures.as_completed(speed_futures), total=len(speed_futures), desc="Testing stream speeds"):
            stream = speed_futures[future]
            try:
                stream['speed'] = future.result()
            except Exception as e:
                stream['speed'] = float('inf')
                print(f"直播源 {stream['link']} 测速时出现异常：{e}")

    valid_streams.sort(key=lambda x: channel_order.index(x["tvg-name"]) if x["tvg-name"] in channel_order else len(channel_order))

    fastest_streams = {}
    for stream in valid_streams:
        tvg_name = stream['tvg-name']
        if tvg_name not in fastest_streams or stream['speed'] < fastest_streams[tvg_name]['speed']:
            fastest_streams[tvg_name] = stream

    with open(output_m3u_filename, 'w', newline='', encoding='utf-8') as m3ufile:
        m3ufile.write('#EXTM3U\n')
        for stream in fastest_streams.values():
            m3ufile.write(f'#EXTINF:-1 tvg-name="{stream["tvg-name"]}" tvg-id="{stream["tvg-id"]}" tvg-logo="{stream["tvg-logo"]}" group-title="{stream["group-title"]}", {stream["tvg-name"]}\n')
            m3ufile.write(f'{stream["link"]}\n')

    grouped_streams = {}
    for stream in valid_streams:
        group_title = stream["group-title"]
        if group_title not in grouped_streams:
            grouped_streams[group_title] = []
        grouped_streams[group_title].append(stream)

    with open(output_txt_filename, 'w', newline='', encoding='utf-8') as txtfile:
        for group_title, streams in grouped_streams.items():
            txtfile.write(f'{group_title},#genre#\n')
            for stream in streams:
                txtfile.write(f'{stream["tvg-name"]},{stream["link"]}\n')
        txtfile.write(f"\n更新时间,#genre#\n")
        txtfile.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},https://vd2.bdstatic.com/mda-phje20fz4z8h126t/720p/h264/1692525385713349507/mda-phje20fz4z8h126t.mp4?v_from_s=hkapp-haokan-hnb&auth_key=1692536679-0-0-384af0ac122eee8fab76c327a47308c4&bcevod_channel=searchbox_feed&cr=2&cd=0&pd=1&pt=3&logid=0279906713&vid=4268605015135290173&klogid=0279906713&abtest=111803_1-112162_2-112345_1\n")
        txtfile.write(f"vip客服:88164962,https://vd2.bdstatic.com/mda-phje20fz4z8h126t/720p/h264/1692525385713349507/mda-phje20fz4z8h126t.mp4?v_from_s=hkapp-haokan-hnb&auth_key=1692536679-0-0-384af0ac122eee8fab76c327a47308c4&bcevod_channel=searchbox_feed&cr=2&cd=0&pd=1&pt=3&logid=0279906713&vid=4268605015135290173&klogid=0279906713&abtest=111803_1-112162_2-112345_1\n")

    print(f"生成新的文件 '{output_m3u_filename}' 和 '{output_txt_filename}' 成功。")

if __name__ == "__main__":
    validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename)
