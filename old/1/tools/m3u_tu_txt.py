import os

def parse_m3u(m3u_file):
    txt_file = os.path.splitext(m3u_file)[0] + ".txt"
    
    with open(m3u_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:-1'):
            info = line.split('tvg-name="')[1].split('"')[0]
            url = lines[i + 1].strip()
            channels.append((info, url))
            i += 1
        i += 1

    with open(txt_file, 'w', encoding='utf-8') as f:
        for channel in channels:
            f.write(f"{channel[0]},{channel[1]}\n")

def convert_all_m3u_files():
    current_directory = os.getcwd()
    for file in os.listdir(current_directory):
        if file.endswith(".m3u"):
            parse_m3u(os.path.join(current_directory, file))

if __name__ == "__main__":
    convert_all_m3u_files()
