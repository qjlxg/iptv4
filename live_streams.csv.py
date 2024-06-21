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
output_csv_filename = 'valid_streams.csv'
log_filename = 'iptv4_error.log'
template_filename = 'moban.txt'  # moban.txt文件名

# 设置日志记录
logging.basicConfig(filename=log_filename, level=logging.ERROR, format='%(asctime)s - %(message)s')

# 创建一个全局的tqdm实例
progress_bar = None

# 读取模板文件中的顺序
def read_template(template_filename):
    order = []
    with open(template_filename, 'r', encoding='utf-8') as templatefile:
        for line in templatefile:
            line = line.strip()
            if line:
                order.append(line)
    return order

# 异步测试直播源链接可用性和速度
async def test_stream_quality(sem, session, stream):
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

# 读取CSV文件
def read_csv(csv_filename):
    streams = []
    with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            streams.append(row)
    return streams

# 生成新的m3u文件，按照模板顺序保留每个tvg-name速度最快的直播源
def generate_m3u_file(valid_streams, output_m3u_filename, template_order):
    # 将有效流按模板顺序排序
    ordered_streams = []
    for tvg_name in template_order:
        for stream in valid_streams:
            if stream['tvg-name'] == tvg_name:
                ordered_streams.append(stream)
                break

    with open(output_m3u_filename, 'w', newline='', encoding='utf-8') as m3ufile:
        m3ufile.write('#EXTM3U\n')
        for stream in ordered_streams:
            m3ufile.write(f'#EXTINF:-1 tvg-name="{stream["tvg-name"]}" tvg-id="{stream["tvg-id"]}" tvg-logo="{stream["tvg-logo"]}" group-title="{stream["group-title"]}", {stream["tvg-name"]}\n')
            m3ufile.write(f'{stream["link"]}\n')

# 生成新的txt文件，按照模板顺序保留每个tvg-name速度最快的10个直播源，并按连接速度排序
def generate_txt_file(valid_streams, output_txt_filename, template_order):
    # 按照模板顺序的group-title顺序
    group_order = [
        "央视频道",
        "卫视频道",
        "影视频道",
        "数字频道",
        "少儿频道",
        "地方频道",
        "港·澳·台"
    ]

    # 根据tvg-name分组，排序每组内的流
    grouped_streams = {}
    for stream in valid_streams:
        tvg_name = stream['tvg-name']
        if tvg_name not in grouped_streams:
            grouped_streams[tvg_name] = []
        grouped_streams[tvg_name].append(stream)

    # 按模板顺序重排并按连接速度排序，每个tvg-name最多保留10个
    ordered_streams = []
    for tvg_name in template_order:
        if tvg_name in grouped_streams:
            streams = grouped_streams[tvg_name]
            streams.sort(key=lambda x: x['speed'])  # 按连接速度排序
            ordered_streams.extend(streams[:10])  # 只保留前10个

    # 按group-title分组
    streams_by_group = {}
    for stream in ordered_streams:
        group_title = stream["group-title"]
        if group_title not in streams_by_group:
            streams_by_group[group_title] = []
        streams_by_group[group_title].append(stream)

    with open(output_txt_filename, 'w', newline='', encoding='utf-8') as txtfile:
        for group_title in group_order:
            if group_title in streams_by_group:
                txtfile.write(f'{group_title},#genre#\n')
                for stream in streams_by_group[group_title]:
                    txtfile.write(f'{stream["tvg-name"]},{stream["link"]}\n')
        txtfile.write(f"\n更新时间,#genre#\n")
        txtfile.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},https://vd2.bdstatic.com/mda-phje20fz4z8h126t/720p/h264/1692525385713349507/mda-phje20fz4z8h126t.mp4?v_from_s=hkapp-haokan-hnb&auth_key=1692536679-0-0-384af0ac122eee8fab76c327a47308c4&bcevod_channel=searchbox_feed&cr=2&cd=0&pd=1&pt=3&logid=0279906713&vid=4268605015135290173&klogid=0279906713&abtest=111803_1-112162_2-112345_1\n")
        txtfile.write(f"vip客服:88164962,https://vd2.bdstatic.com/mda-phje20fz4z8h126t/720p/h264/1692525385713349507/mda-phje20fz4z8h126t.mp4?v_from_s=hkapp-haokan-hnb&auth_key=1692536679-0-0-384af0ac122eee8fab76c327a47308c4&bcevod_channel=searchbox_feed&cr=2&cd=0&pd=1&pt=3&logid=0279906713&vid=4268605015135290173&klogid=0279906713&abtest=111803_1-112162_2-112345_1\n")

# 将有效直播源写入新的CSV文件，按照模板顺序一级排序，并且对相同tvg-name的直播源按速度二级排序
def write_valid_streams_to_csv(valid_streams, output_csv_filename, template_order):
    # 创建一个字典用于存储每个tvg-name对应的所有直播源
    sorted_streams = {}
    
    # 将valid_streams按照tvg-name进行分组
    for stream in valid_streams:
        tvg_name = stream['tvg-name']
        if tvg_name not in sorted_streams:
            sorted_streams[tvg_name] = []
        sorted_streams[tvg_name].append(stream)
    
    # 依次按照模板顺序将每组tvg-name的直播源排序并写入CSV文件
    with open(output_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['tvg-name', 'tvg-id', 'tvg-logo', 'group-title', 'link', 'speed']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for tvg_name in template_order:
            if tvg_name in sorted_streams:
                streams = sorted_streams[tvg_name]
                # 对相同tvg-name的直播源按速度进行排序
                streams.sort(key=lambda x: x['speed'])
                for stream in streams:
                    writer.writerow(stream)

# 验证直播源并生成文件
async def validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, output_csv_filename, template_filename):
    global progress_bar
    valid_streams = []
    streams = read_csv(csv_filename)

    # 创建tqdm实例并设置总长度
    progress_bar = tqdm(total=len(streams), desc="Validating streams")

    # 创建信号量，控制并发数量
    sem = asyncio.Semaphore(50)

    async with aiohttp.ClientSession() as session:
        tasks = [test_stream_quality(sem, session, stream) for stream in streams]
        results = await asyncio.gather(*tasks)

    for result in results:
        if result['available']:
            valid_streams.append(result['stream'])

    # 关闭进度条
    progress_bar.close()

    # 读取模板文件中的顺序
    template_order = read_template(template_filename)

    # 生成新的m3u文件，按照模板顺序保留每个tvg-name速度最快的直播源
    generate_m3u_file(valid_streams, output_m3u_filename, template_order)

    # 生成新的txt文件，按照模板顺序保留每个tvg-name速度最快的10个直播源，并按连接速度排序
    generate_txt_file(valid_streams, output_txt_filename, template_order)

    # 将有效直播源写入新的CSV文件，按照模板顺序
    write_valid_streams_to_csv(valid_streams, output_csv_filename, template_order)

    print(f"生成新的文件 '{output_m3u_filename}', '{output_txt_filename}' 和 '{output_csv_filename}' 成功。")

# 主程序入口
if __name__ == "__main__":
    asyncio.run(validate_and_generate_files(csv_filename, output_m3u_filename, output_txt_filename, output_csv_filename, template_filename))
