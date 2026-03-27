import json
import re
import requests
import base64

# ---------------------------
# CONFIG
# ---------------------------
SPORTS_API = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"
REFERER = "https://edge.cdn-live.ru/"
OUTPUT_FILE = "cdn-live.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": REFERER
}

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------
# DEOBFUSCATION (UNCHANGED)
# ---------------------------
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


# ---------------------------
# EXTRACT M3U8 FROM PLAYER PAGE
# ---------------------------
def get_m3u8_url(channel_url):
    try:
        response = session.get(channel_url, timeout=10)
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

        deobfuscated_code = deobfuscate(h, n, t, e)

        src_match = re.search(r"src:\s*([\w\d]+)", deobfuscated_code)
        if not src_match:
            return None

        src_variable_name = src_match.group(1)

        assignment_regex = r"const\s+" + re.escape(src_variable_name) + r"\s*=\s*(.*?);"
        assignment_match = re.search(assignment_regex, deobfuscated_code)

        if not assignment_match:
            return None

        assignment_line = assignment_match.group(1)

        decoder_func_match = re.search(r"function\s+([a-zA-Z0-9_]+)\(str\)", deobfuscated_code)
        if not decoder_func_match:
            return None

        decoder_func_name = decoder_func_match.group(1)

        parts_vars_regex = re.escape(decoder_func_name) + r"\((\w+)\)"
        parts_vars = re.findall(parts_vars_regex, assignment_line)

        const_declarations = re.findall(r"const\s+(\w+)\s+=\s+'([^']+)';", deobfuscated_code)
        parts_dict = {match[0]: match[1] for match in const_declarations}

        url_parts_b64 = [parts_dict[var_name] for var_name in parts_vars]
        decoded_parts = [LEUlrDBkdbMl(part) for part in url_parts_b64]

        return "".join(decoded_parts)

    except Exception:
        return None


# ---------------------------
# FETCH SPORTS CHANNELS
# ---------------------------
def fetch_sports_channels():
    res = session.get(SPORTS_API, timeout=10)
    res.raise_for_status()

    data = res.json().get("data", [])
    channels = []

    for event in data:
        event_name = event.get("title", "Unknown Event")

        for ch in event.get("channels", []):
            ch["event_name"] = event_name
            channels.append(ch)

    return channels


# ---------------------------
# BUILD PLAYLIST
# ---------------------------
def build_playlist(channels):
    lines = ["#EXTM3U"]

    success = 0
    failed = 0

    for ch in channels:
        name = ch.get("name", "Unknown Channel")
        event = ch.get("event_name", "Unknown Event")
        player_url = ch.get("url")

        full_name = f"{event} - {name}"
        print(f"Processing: {full_name}")

        if not player_url:
            print(f"FAILED (no url): {full_name}")
            failed += 1
            continue

        stream = get_m3u8_url(player_url)

        if stream:
            lines.append(f'#EXTINF:-1,{full_name}')
            lines.append(f'#EXTVLCOPT:http-referrer={REFERER}')
            lines.append(stream)
            success += 1
        else:
            print(f"FAILED: {full_name}")
            failed += 1

    print("\n====================")
    print(f"TOTAL CHANNELS: {success}")
    print(f"FAILED: {failed}")
    print("====================")

    return "\n".join(lines)


# ---------------------------
# MAIN
# ---------------------------
def main():
    channels = fetch_sports_channels()
    playlist = build_playlist(channels)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
