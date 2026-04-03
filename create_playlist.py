import re
import random
import requests
import base64
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PROXY      = "http://192.168.1.101:8090/proxy?url="
REFERER    = "https://edge.cdn-live.ru/"
MAX_WORKERS = 5

# ---------------------------
# 🌍 FLAG MAP
# ---------------------------
FLAG_MAP = {
    "us": "🇺🇸", "uk": "🇬🇧", "gb": "🇬🇧", "ca": "🇨🇦",
    "au": "🇦🇺", "nz": "🇳🇿",
    "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
    "pt": "🇵🇹", "nl": "🇳🇱", "be": "🇧🇪", "ch": "🇨🇭",
    "at": "🇦🇹", "se": "🇸🇪", "no": "🇳🇴", "dk": "🇩🇰",
    "fi": "🇫🇮", "ie": "🇮🇪", "pl": "🇵🇱", "cz": "🇨🇿",
    "sk": "🇸🇰", "hu": "🇭🇺", "ro": "🇷🇴", "bg": "🇧🇬",
    "gr": "🇬🇷", "tr": "🇹🇷", "ua": "🇺🇦", "ru": "🇷🇺",
    "rs": "🇷🇸", "hr": "🇭🇷", "si": "🇸🇮", "ba": "🇧🇦",
    "mk": "🇲🇰", "al": "🇦🇱",
    "ae": "🇦🇪", "sa": "🇸🇦", "qa": "🇶🇦", "kw": "🇰🇼",
    "om": "🇴🇲", "bh": "🇧🇭", "il": "🇮🇱", "ir": "🇮🇷",
    "iq": "🇮🇶", "jo": "🇯🇴", "lb": "🇱🇧", "sy": "🇸🇾",
    "in": "🇮🇳", "pk": "🇵🇰", "bd": "🇧🇩", "lk": "🇱🇰",
    "np": "🇳🇵", "af": "🇦🇫",
    "sg": "🇸🇬", "my": "🇲🇾", "th": "🇹🇭", "id": "🇮🇩",
    "ph": "🇵🇭", "vn": "🇻🇳", "kh": "🇰🇭",
    "jp": "🇯🇵", "kr": "🇰🇷", "cn": "🇨🇳", "tw": "🇹🇼",
    "hk": "🇭🇰",
    "za": "🇿🇦", "eg": "🇪🇬", "ng": "🇳🇬", "ke": "🇰🇪",
    "ma": "🇲🇦", "dz": "🇩🇿", "tn": "🇹🇳", "gh": "🇬🇭",
    "br": "🇧🇷", "ar": "🇦🇷", "mx": "🇲🇽", "cl": "🇨🇱",
    "co": "🇨🇴", "pe": "🇵🇪", "ve": "🇻🇪",
    "uy": "🇺🇾", "py": "🇵🇾", "bo": "🇧🇴",
    "cr": "🇨🇷", "pa": "🇵🇦", "gt": "🇬🇹", "cu": "🇨🇺",
    "do": "🇩🇴", "jm": "🇯🇲",
    "int": "🌍", "global": "🌍",
}

# ---------------------------
# DEOBFUSCATION
# ---------------------------
def _0xe35c(d, e, f):
    g = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
    h_chars = g[:e]
    i_chars = g[:f]
    j = 0
    for i, c in enumerate(d[::-1]):
        if c in h_chars:
            j += h_chars.index(c) * (e ** i)
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
# STREAM URL EXTRACTOR
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
                    params_str, re.DOTALL
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
                            parts_decoded = [decode_part(consts[v]) for v in vars_used if v in consts]
                            final = "".join(parts_decoded)
                            if final.startswith("http"):
                                return final

            m3u8 = re.search(r'https?://[^"\']+\.m3u8[^"\']*', html)
            if m3u8:
                return m3u8.group(0)

        except Exception:
            pass
        time.sleep(0.3)
    return None

# ---------------------------
# PROCESS ONE CHANNEL
# ---------------------------
def process_channel(ch):
    # Random jitter to avoid thundering herd
    time.sleep(random.uniform(0.5, 1.5))

    if not ch.get("stream_url"):
        return None

    m3u8 = get_m3u8_url(ch["stream_url"])
    if not m3u8:
        return None

    code = (ch.get("code") or "").lower()
    flag = FLAG_MAP.get(code, code.upper())
    name = f'{ch["name"]} {flag}'.strip()

    encoded   = urllib.parse.quote(m3u8, safe='')
    proxy_url = PROXY + encoded

    return {
        "name":     name,
        "raw_name": ch["name"],
        "code":     ch.get("code", ""),
        "logo":     ch.get("logo", ""),
        "category": ch.get("category", "Live TV"),
        "url":      proxy_url,
    }

# ---------------------------
# CHANNELS API
# Single fetch — API ignores ?page= and returns the same data every time
# ---------------------------
def get_channels():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": REFERER
    }
    try:
        response = requests.get(
            "https://api.cdn-live.tv/api/v1/channels/?user=cdnlivetv&plan=free",
            headers=headers,
            timeout=10
        )
        data = response.json()
        channels = data.get("channels", [])

        seen = set()
        results = []
        for ch in channels:
            if ch.get("status") != "online":
                continue
            key = (ch.get("code"), ch.get("name"))
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "name":       ch.get("name"),
                "code":       ch.get("code"),
                "logo":       ch.get("image"),
                "stream_url": ch.get("url"),
                "category":   ch.get("category", "Live TV"),
            })

        print(f"  Got {len(results)} unique online channels")
        return results

    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []

# ---------------------------
# MAIN
# ---------------------------
def main():
    print("Fetching channel list...")
    channels = get_channels()
    print(f"Found {len(channels)} channels\n")

    if not channels:
        print("No channels found.")
        return

    print(f"Extracting stream URLs with {MAX_WORKERS} workers...\n")

    results = []
    failed  = 0
    done    = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_channel, ch): ch for ch in channels}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                results.append(result)
                print(f"[{done}/{len(channels)}] ✓ {result['name']}")
            else:
                ch = futures[future]
                failed += 1
                print(f"[{done}/{len(channels)}] ✗ {ch.get('name', '?')} (no stream found)")

    results.sort(key=lambda x: (x["category"], x["name"]))

    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for r in results:
            f.write(
                f'#EXTINF:-1 tvg-id="{r["code"]}" tvg-name="{r["raw_name"]}" '
                f'tvg-logo="{r["logo"]}" group-title="{r["category"]}",{r["name"]}\n'
            )
            f.write(f'#EXTVLCOPT:http-referrer={REFERER}\n')
            f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
            f.write(r["url"] + "\n")

    print(f"\n{'='*40}")
    print(f"DONE — {len(results)} working / {failed} failed / {len(channels)} total")
    print(f"Saved to cdn-live.m3u")

if __name__ == "__main__":
    main()
