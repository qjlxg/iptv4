import csv
import cv2
import requests
from tqdm import tqdm
from datetime import datetime
import concurrent.futures

# CSV文件名和输出文件名
csv_filename = 'live_streams.csv'
output_m3u_filename = 'iptv4.m3u'
output_txt_filename = 'iptv4.txt'
moban_filename = 'moban.txt'

# 验证直播源的可用性
def test_stream_availability(stream_link):
    try:
        cap = cv2.VideoCapture(stream_link)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return ret
        else:
            return False
    except Exception as e:
        print(f"Exception while testing stream {stream_link}: {str(e)}")
        return False

# 测试直播源链接速度
def test_stream_speed(stream_link):
    try:
        start_time = datetime.now()
        response = requests.get(stream_link, stream=True, timeout=5)
        if response.status_code == 200:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            return duration
        else:
            return float('inf')
    except Exception as e:
        print(f"Exception while testing speed for stream {stream_link}: {str(e)}")
        return float('inf')

# 读取moban.txt文件中的频道名称
def read_moban_file(moban_filename):
    with open(moban_filename, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file]

# 读取csv文件并去重
def read_and_deduplicate_csv(csv_filename):
    unique_streams = {}
    with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            link = row['link']
            if link not in unique_streams:
                unique_streams[link] = row
    return list(unique_streams.values())

# 验证live_streams.csv中直播源的有效性，并生成新的m3u和txt文件
def validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename):
    valid_streams = []
    channel_order = read_moban_file(moban_filename)
    unique_streams = read_and_deduplicate_csv(csv_filename)
    
    def validate_stream(row):
        try:
            if test_stream_availability(row['link']):
                return row
            else:
                print(f"直播源 {row['link']} 不可用，将被忽略。")
                return None
        except Exception as e:
            print(f"直播源 {row['link']} 检测时出现异常：{e}")
            return None
    
    # 使用ThreadPoolExecutor进行并行验证
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(validate_stream, row) for row in unique_streams]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Validating streams"):
            result = future.result()
            if result:
                valid_streams.append(result)
    
    # 去掉没有tvg-name或link字段的直播源
    valid_streams = [stream for stream in valid_streams if stream.get('tvg-name') and stream.get('link')]
    
    def test_speed(stream):
        try:
            stream['speed'] = test_stream_speed(stream['link'])
        except Exception as e:
            stream['speed'] = float('inf')
            print(f"直播源 {stream['link']} 测速时出现异常：{e}")
        return stream
    
    # 使用ThreadPoolExecutor进行并行速度测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        valid_streams = list(tqdm(executor.map(test_speed, valid_streams), total=len(valid_streams), desc="Testing stream speeds"))

    # 按moban.txt文件中的顺序排序
    valid_streams.sort(key=lambda x: channel_order.index(x["tvg-name"]) if x["tvg-name"] in channel_order else len(channel_order))
    
    # 生成新的m3u文件，保留每个tvg-name速度最快的直播源
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

    # 生成新的txt文件，保留所有有效的直播源
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

# 主程序入口
if __name__ == "__main__":
    validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename)
