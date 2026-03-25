import json
import re
import requests
import base64
import urllib.parse

PROXY = "https://arx-fin-live.vercel.app/api/proxy?url="

# --- DEOBFUSCATION HELPERS ---

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

def decode_part(s):
    s = s.replace('-', '+').replace('_', '/')
    while len(s) % 4:
        s += '='
    return base64.b64decode(s).decode('utf-8')

# --- EXTRACT STREAM ---

def get_m3u8_url(channel_url, referer):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer
    }

    try:
        response = requests.get(channel_url, headers=headers)
        response.raise_for_status()
        html = response.text

        match = re.search(r'eval\(function\(h,u,n,t,e,r\)\{.*?\}\((.*?)\)\)', html, re.DOTALL)
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

        parts = [decode_part(consts[v]) for v in vars_used if v in consts]

        return "".join(parts)

    except:
        return None

# --- SPORTS API ---

def get_event_channels():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://edge.cdn-live.ru/"
    }

    try:
        response = requests.get(
            "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free",
            headers=headers
        )
        response.raise_for_status()

        data = response.json().get("cdn-live-tv", {})
        results = []

        for sport in data:
            if not isinstance(data[sport], list):
                continue

            for match in data[sport]:
                title = f"{match.get('homeTeam')} vs {match.get('awayTeam')}"
                tournament = match.get("tournament")
                time = match.get("time")

                for ch in match.get("channels", []):
                    results.append({
                        "title": title,
                        "tournament": tournament,
                        "time": time,
                        "channel_name": ch.get("channel_name"),
                        "stream_url": ch.get("url"),
                        "logo": ch.get("image"),
                        "code": ch.get("channel_code")
                    })

        return results

    except Exception as e:
        print(f"Error fetching events: {e}")
        return []

# --- MAIN ---

referer_url = "https://edge.cdn-live.ru/"
channels = get_event_channels()

# optional limit (safe)
channels = channels[:20]

if channels:
    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')

        for ch in channels:
            print(f"Processing {ch['title']} ({ch['channel_name']})...")

            m3u8 = get_m3u8_url(ch["stream_url"], referer_url)

            if m3u8:
                # proxy encode
                encoded = urllib.parse.quote(m3u8, safe='')
                proxy_url = PROXY + encoded

                # better naming for Jellyfin
                name = f"{ch['title']} [{ch['tournament']}] ({ch['channel_name']})"

                f.write(f'#EXTINF:-1 tvg-id="{ch["code"]}" tvg-name="{name}" tvg-logo="{ch["logo"]}" group-title="{ch["tournament"]}",{name}\n')
                f.write(f'#EXTVLCOPT:http-referrer={referer_url}\n')
                f.write(f"{proxy_url}\n")

    print("Playlist created successfully.")

else:
    print("No streams found.")
