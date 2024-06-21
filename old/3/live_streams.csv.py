import cv2
import csv
import asyncio
from tqdm import tqdm
from datetime import datetime

# CSV文件名和输出文件名
csv_filename = 'live_streams.csv'
output_m3u_filename = 'iptv4.m3u'
output_txt_filename = 'iptv4.txt'
moban_filename = 'moban.txt'

# 同步测试直播源链接可用性
def test_stream_availability(stream):
    try:
        cap = cv2.VideoCapture(stream['link'])
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return {'stream': stream, 'available': ret}
        return {'stream': stream, 'available': False}
    except Exception as e:
        print(f"Exception while testing stream {stream['link']}: {str(e)}")
        return {'stream': stream, 'available': False}

# 读取csv文件
def read_csv(csv_filename):
    streams = []
    with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            streams.append(row)
    return streams

# 生成新的m3u文件，保留每个tvg-name速度最快的直播源
def generate_m3u_file(valid_streams, output_m3u_filename):
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
def generate_txt_file(valid_streams, output_txt_filename):
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

# 验证直播源并生成文件
async def validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename):
    valid_streams = []
    streams = read_csv(csv_filename)
    
    for stream in tqdm(streams, desc="Validating streams"):
        result = test_stream_availability(stream)
        if result['available']:
            valid_streams.append(result['stream'])
        else:
            print(f"直播源 {result['stream']['link']} 不可用，将被忽略。")
    
    # 生成新的m3u文件，保留每个tvg-name速度最快的直播源
    generate_m3u_file(valid_streams, output_m3u_filename)
    
    # 生成新的txt文件，保留所有有效的直播源
    generate_txt_file(valid_streams, output_txt_filename)
    
    print(f"生成新的文件 '{output_m3u_filename}' 和 '{output_txt_filename}' 成功。")

# 主程序入口
if __name__ == "__main__":
    asyncio.run(validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, moban_filename))
