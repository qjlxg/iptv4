import csv
import asyncio
import aiohttp
from tqdm import tqdm
from datetime import datetime
import logging

# CSV文件名和输出文件名
csv_filename = 'live_streams.csv'
output_m3u_filename = 'iptv4.m3u'
output_txt_filename = 'iptv4.txt'
log_filename = 'iptv4_error.log'

# 设置日志记录
logging.basicConfig(filename=log_filename, level=logging.ERROR, format='%(asctime)s - %(message)s')

# 创建一个全局的tqdm实例
progress_bar = None

# 异步测试直播源链接可用性
async def test_stream_availability(sem, session, stream):
    global progress_bar
    try:
        if 'link' not in stream:
            raise ValueError("Stream data is missing 'link' information")
        
        async with sem:
            start_time = datetime.now()
            async with session.get(stream['link'], timeout=5) as response:
                response.raise_for_status()  # 抛出异常如果响应状态码不是200
                end_time = datetime.now()
                stream['speed'] = (end_time - start_time).total_seconds()  # 计算响应速度
            
            progress_bar.update(1)
            return {'stream': stream, 'available': True}
    
    except (aiohttp.ClientError, ValueError, asyncio.TimeoutError) as e:
        logging.error(f"Error testing stream {stream.get('link', 'unknown link')}: {str(e)}")
        progress_bar.update(1)
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

# 生成新的txt文件，保留每个tvg-name速度最快的前10条有效的直播源
def generate_txt_file(valid_streams, output_txt_filename):
    # 去重和按速度排序
    unique_streams = {}
    for stream in valid_streams:
        tvg_name = stream['tvg-name']
        if tvg_name not in unique_streams:
            unique_streams[tvg_name] = []
        unique_streams[tvg_name].append(stream)

    # 保留每个tvg-name速度最快的前10条有效的直播源
    filtered_streams = []
    for tvg_name, streams in unique_streams.items():
        # 按速度从小到大排序
        streams.sort(key=lambda x: x['speed'])
        # 保留前10条
        filtered_streams.extend(streams[:10])

    grouped_streams = {}
    for stream in filtered_streams:
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
async def validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename):
    global progress_bar
    valid_streams = []
    streams = read_csv(csv_filename)
    
    # 创建tqdm实例并设置总长度
    progress_bar = tqdm(total=len(streams), desc="Validating streams")
    
    # 创建信号量，控制并发数量
    sem = asyncio.Semaphore(50)
    
    async with aiohttp.ClientSession() as session:
        tasks = [test_stream_availability(sem, session, stream) for stream in streams]
        results = await asyncio.gather(*tasks)
    
    for result in results:
        if result['available']:
            valid_streams.append(result['stream'])
    
    # 关闭进度条
    progress_bar.close()
    
    # 生成新的m3u文件，保留每个tvg-name速度最快的直播源
    generate_m3u_file(valid_streams, output_m3u_filename)
    
    # 生成新的txt文件，保留所有有效的直播源
    generate_txt_file(valid_streams, output_txt_filename)
    
    print(f"生成新的文件 '{output_m3u_filename}' 和 '{output_txt_filename}' 成功。")

# 主程序入口
if __name__ == "__main__":
    asyncio.run(validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename))
