import json
import re
import requests
import base64
import urllib.parse
import time

PROXY = "http://192.168.1.101:8090/stream?url="
REFERER = "https://edge.cdn-live.ru/"

# ---------------------------
# 🌍 FULL FLAG MAP
# ---------------------------
FLAG_MAP = {
    # Major
    "us": "🇺🇸", "uk": "🇬🇧", "gb": "🇬🇧", "ca": "🇨🇦",
    "au": "🇦🇺", "nz": "🇳🇿",

    # Europe
    "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
    "pt": "🇵🇹", "nl": "🇳🇱", "be": "🇧🇪", "ch": "🇨🇭",
    "at": "🇦🇹", "se": "🇸🇪", "no": "🇳🇴", "dk": "🇩🇰",
    "fi": "🇫🇮", "ie": "🇮🇪", "pl": "🇵🇱", "cz": "🇨🇿",
    "sk": "🇸🇰", "hu": "🇭🇺", "ro": "🇷🇴", "bg": "🇧🇬",
    "gr": "🇬🇷", "tr": "🇹🇷", "ua": "🇺🇦", "ru": "🇷🇺",

    # Balkans
    "rs": "🇷🇸", "hr": "🇭🇷", "si": "🇸🇮", "ba": "🇧🇦",
    "mk": "🇲🇰", "al": "🇦🇱",

    # Middle East
    "ae": "🇦🇪", "sa": "🇸🇦", "qa": "🇶🇦", "kw": "🇰🇼",
    "om": "🇴🇲", "bh": "🇧🇭", "il": "🇮🇱", "ir": "🇮🇷",
    "iq": "🇮🇶", "jo": "🇯🇴", "lb": "🇱🇧", "sy": "🇸🇾",

    # South Asia
    "in": "🇮🇳", "pk": "🇵🇰", "bd": "🇧🇩", "lk": "🇱🇰",
    "np": "🇳🇵", "af": "🇦🇫",

    # Southeast Asia
    "sg": "🇸🇬", "my": "🇲🇾", "th": "🇹🇭", "id": "🇮🇩",
    "ph": "🇵🇭", "vn": "🇻🇳", "kh": "🇰🇭",

    # East Asia
    "jp": "🇯🇵", "kr": "🇰🇷", "cn": "🇨🇳", "tw": "🇹🇼",
    "hk": "🇭🇰",

    # Africa
    "za": "🇿🇦", "eg": "🇪🇬", "ng": "🇳🇬", "ke": "🇰🇪",
    "ma": "🇲🇦", "dz": "🇩🇿", "tn": "🇹🇳", "gh": "🇬🇭",

    # Americas
    "br": "🇧🇷", "ar": "🇦🇷", "mx": "🇲🇽", "cl": "🇨🇱",
    "co": "🇨🇴", "pe": "🇵🇪", "ve": "🇻🇪",
    "uy": "🇺🇾", "py": "🇵🇾", "bo": "🇧🇴",

    # Central / Caribbean
    "cr": "🇨🇷", "pa": "🇵🇦", "gt": "🇬🇹", "cu": "🇨🇺",
    "do": "🇩🇴", "jm": "🇯🇲",

    # Generic
    "int": "🌍", "global": "🌍",
}

# ---------------------------
# 🧠 EPG MAP
# ---------------------------
EPG_MAP = {
    "espn": "espn.us",
    "espn 2": "espn2.us",
    "sky sports main event": "skysportsmainevent.uk",
    "sky sports premier league": "skysportspremierleague.uk",
    "sony ten 1": "sonyten1.in",
    "sony ten 2": "sonyten2.in",
    "sony ten 3": "sonyten3.in",
    "bein sports": "beinsports1.qa"
}

# ---------------------------
# DEOBFUSCATION (UNCHANGED)
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
# EXTRACTOR (UNCHANGED)
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
# CHANNELS API (UNCHANGED)
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

        data = response.json().get("channels", [])

        results = []

        for ch in data:
            if ch.get("status") != "online":
                continue

            results.append({
                "name": ch.get("name"),
                "code": ch.get("code"),
                "logo": ch.get("image"),
                "stream_url": ch.get("url"),
                "category": ch.get("category", "Live TV")
            })

        return results

    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []


# ---------------------------
# MAIN
# ---------------------------
def main():
    channels = get_channels()

    print(f"Fetched {len(channels)} channels")

    if not channels:
        print("No channels found.")
        return

    used_ids = {}

    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        success = 0

        for ch in channels:
            raw_name = ch.get("name") or ""
            code = (ch.get("code") or "").lower()

            clean = raw_name.lower()
            clean = re.sub(r'[^a-z0-9 ]', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()

            tvg_id = None
            for key in EPG_MAP:
                if key in clean:
                    tvg_id = EPG_MAP[key]
                    break

            if not tvg_id:
                base = clean.replace(" ", ".")
                tvg_id = f"{base}.{code}" if code else base

            if tvg_id in used_ids:
                used_ids[tvg_id] += 1
                tvg_id = f"{tvg_id}.{used_ids[tvg_id]}"
            else:
                used_ids[tvg_id] = 1

            flag = FLAG_MAP.get(code, "🏳️")
            name = f'{flag} {raw_name}'.strip()

            print(f"Processing: {name}")

            if not ch["stream_url"]:
                continue

            time.sleep(1.2)

            m3u8 = get_m3u8_url(ch["stream_url"])

            if m3u8:
                encoded = urllib.parse.quote(m3u8, safe='')
                proxy_url = PROXY + encoded

                f.write(
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{raw_name}" '
                    f'tvg-logo="{ch["logo"]}" group-title="{ch["category"]}",{name}\n'
                )
                f.write(f'#EXTVLCOPT:http-referrer={REFERER}\n')
                f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
                f.write(proxy_url + "\n")

                success += 1

        print(f"\nTOTAL WORKING: {success}")


if __name__ == "__main__":
    main()
