import json
import re
import requests
import base64
from urllib.parse import unquote
import urllib.parse   # ✅ ADDED

PROXY = "https://arx-fin-live.vercel.app/api/proxy?url="  # ✅ ADDED

def _0xe35c(d, e, f):
    g = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
    h_chars = g[:e]
    i_chars = g[:f]
    
    j = 0
    d_reversed = d[::-1]
    for c_idx, c_val in enumerate(d_reversed):
        if c_val in h_chars:
            j += h_chars.index(c_val) * (e**c_idx)

    if j == 0:
        return '0'
        
    k = ''
    while j > 0:
        k = i_chars[j % f] + k
        j = (j - (j % f)) // f
        
    return k if k else '0'

def deobfuscate(h, n, t, e):
    r = ""
    i = 0
    len_h = len(h)
    
    delimiter = n[e]
    n_map = {char: str(idx) for idx, char in enumerate(n)}

    while i < len_h:
        s = ""
        while i < len_h and h[i] != delimiter:
            s += h[i]
            i += 1
        
        i += 1
        
        if s:
            s_digits = "".join([n_map.get(c, c) for c in s])
            char_code = int(_0xe35c(s_digits, e, 10)) - t
            r += chr(char_code)
            
    return r

def LEUlrDBkdbMl(s):
    s = s.replace('-', '+').replace('_', '/')
    while len(s) % 4:
        s += '='
    return base64.b64decode(s).decode('utf-8')

def get_m3u8_url(channel_url, referer):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer
    }
    
    try:
        response = requests.get(channel_url, headers=headers)
        response.raise_for_status()
        html_content = response.text

        match = re.search(r'eval\(function\(h,u,n,t,e,r\)\{.*?\}\((.*?)\)\)', html_content, re.DOTALL)
        if not match:
            return None

        params_str = match.group(1).strip()

        params_match = re.search(
            r'([\'"])((?:(?!\1).)*)\1,\s*\d+,\s*([\'"])((?:(?!\3).)*)\3,\s*(\d+),\s*(\d+)',
            params_str,
            re.DOTALL
        )

        if not params_match:
            return None

        h = params_match.group(2)
        n = params_match.group(4)
        t = int(params_match.group(5))
        e = int(params_match.group(6))

        decoded = deobfuscate(h, n, t, e)

        src_match = re.search(r"src:\s*([\w\d]+)", decoded)
        if not src_match:
            return None

        var_name = src_match.group(1)

        assignment = re.search(rf"const\s+{var_name}\s*=\s*(.*?);", decoded)
        if not assignment:
            return None

        line = assignment.group(1)

        decoder_func = re.search(r"function\s+([a-zA-Z0-9_]+)\(str\)", decoded)
        if not decoder_func:
            return None

        func_name = decoder_func.group(1)

        vars_used = re.findall(rf"{func_name}\((\w+)\)", line)

        consts = dict(re.findall(r"const\s+(\w+)\s+=\s+'([^']+)'", decoded))

        parts = [LEUlrDBkdbMl(consts[v]) for v in vars_used if v in consts]

        return "".join(parts)

    except:
        return None

def get_online_channels(referer):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer
    }
    try:
        response = requests.get(
            "https://api.cdn-live.tv/api/v1/channels/?user=cdnlivetv&plan=free",
            headers=headers
        )
        response.raise_for_status()

        all_channels = response.json().get('channels', [])
        return [ch for ch in all_channels if ch.get('status') == 'online']

    except:
        return []

referer_url = "https://edge.cdn-live.ru/"
channels_data = get_online_channels(referer_url)

if channels_data:
    with open("cdn-live.m3u", "w", encoding='utf-8') as f:
        f.write('#EXTM3U\n')

        for channel in channels_data:
            print(f"Processing {channel.get('name')}...")

            player_page_url = channel.get('url')
            if not player_page_url:
                continue

            m3u8_url = get_m3u8_url(player_page_url, referer_url)

            if m3u8_url:
                name = channel.get('name')
                code = channel.get('code')
                logo = channel.get('image')

                # ✅ PROXY CONVERSION
                encoded = urllib.parse.quote(m3u8_url, safe='')
                proxy_url = PROXY + encoded

                f.write(f'#EXTINF:-1 tvg-id="{code}" tvg-name="{name}" tvg-logo="{logo}",{name}\n')
                f.write(f'#EXTVLCOPT:http-referrer={referer_url}\n')
                f.write(f"{proxy_url}\n")

    print("Playlist created successfully.")
else:
    print("No channels found.")
