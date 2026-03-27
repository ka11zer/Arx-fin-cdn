import json
import re
import requests
import base64
import urllib.parse
import time

PROXY = "http://192.168.1.101:8090/stream?url="
REFERER = "https://edge.cdn-live.ru/"

# ---------------------------
# SIAM DEOBFUSCATION
# ---------------------------
def _0xe35c(d, e, f):
    g = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
    h_chars = g[:e]
    i_chars = g[:f]

    j = 0
    for i, c in enumerate(d[::-1]):
        if c in h_chars:
            j += h_chars.index(c) * (e**i)

    if j == 0:
        return '0'

    k = ''
    while j > 0:
        k = i_chars[j % f] + k
        j //= f

    return k


def deobfuscate(h, n, t, e):
    r = ""
    i = 0
    delimiter = n[e]
    n_map = {char: str(idx) for idx, char in enumerate(n)}

    while i < len(h):
        s = ""
        while i < len(h) and h[i] != delimiter:
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


# ---------------------------
# EXTRACTOR (RETRY)
# ---------------------------
def get_m3u8_url(channel_url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": REFERER
    }

    for attempt in range(3):
        try:
            response = requests.get(channel_url, headers=headers, timeout=15)
            html = response.text

            match = re.search(r'eval\(function\(h,u,n,t,e,r\)\{.*?\}\((.*?)\)\)', html, re.DOTALL)

            if match:
                params_str = match.group(1)

                parts = re.search(
                    r'([\'"])(.*?)\1,\s*\d+,\s*([\'"])(.*?)\3,\s*(\d+),\s*(\d+)',
                    params_str,
                    re.DOTALL
                )

                if parts:
                    h = parts.group(2)
                    n = parts.group(4)
                    t = int(parts.group(5))
                    e = int(parts.group(6))

                    decoded = deobfuscate(h, n, t, e)

                    src = re.search(r"src:\s*(\w+)", decoded)
                    if src:
                        var = src.group(1)

                        assign = re.search(rf"const\s+{var}\s*=\s*(.*?);", decoded)
                        func_match = re.search(r"function\s+(\w+)\(str\)", decoded)

                        if assign and func_match:
                            line = assign.group(1)
                            func = func_match.group(1)

                            vars_used = re.findall(rf"{func}\((\w+)\)", line)
                            consts = dict(re.findall(r"const\s+(\w+)\s+=\s+'([^']+)'", decoded))

                            parts = [decode_part(consts[v]) for v in vars_used if v in consts]
                            final = "".join(parts)

                            if final.startswith("http"):
                                return final

            m3u8 = re.search(r'https?://[^"\']+\.m3u8[^"\']*', html)
            if m3u8:
                return m3u8.group(0)

        except Exception:
            pass

        time.sleep(0.5)

    return None


# ---------------------------
# SPORTS API
# ---------------------------
def get_event_channels():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": REFERER
    }

    try:
        response = requests.get(
            "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free",
            headers=headers,
            timeout=10
        )

        data = response.json().get("cdn-live-tv", {})

        results = []

        for sport in data:
            if not isinstance(data[sport], list):
                continue

            for match in data[sport]:
                title = f"{match.get('homeTeam')} vs {match.get('awayTeam')}"
                tournament = match.get("tournament")

                for ch in match.get("channels", []):
                    results.append({
                        "title": title,
                        "tournament": tournament,
                        "channel_name": ch.get("channel_name"),
                        "stream_url": ch.get("url"),
                        "logo": ch.get("image"),
                        "code": ch.get("channel_code")
                    })

        return results

    except Exception as e:
        print(f"Error fetching events: {e}")
        return []


# ---------------------------
# MAIN
# ---------------------------
def main():
    channels = get_event_channels()

    print(f"Fetched {len(channels)} channels")

    if not channels:
        print("No streams found.")
        return

    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        success = 0

        for ch in channels:
            name = f"{ch['title']} [{ch['tournament']}] ({ch['channel_name']})"
            print(f"Processing: {name}")

            if not ch["stream_url"]:
                continue

            # 🔥 anti-ban delay
            time.sleep(1.5)

            m3u8 = get_m3u8_url(ch["stream_url"])

            if m3u8:
                encoded = urllib.parse.quote(m3u8, safe='')
                proxy_url = PROXY + encoded

                f.write(f'#EXTINF:-1 group-title="{ch["tournament"]}",{name}\n')
                f.write(f'#EXTVLCOPT:http-referrer={REFERER}\n')
                f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
                f.write(proxy_url + "\n")

                success += 1

        print(f"\nTOTAL WORKING: {success}")


if __name__ == "__main__":
    main()
