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
    "us": "🇺🇸", "uk": "🇬🇧", "gb": "🇬🇧", "ca": "🇨🇦",
    "au": "🇦🇺", "nz": "🇳🇿",
    "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹",
    "pt": "🇵🇹", "nl": "🇳🇱", "be": "🇧🇪", "ch": "🇨🇭",
    "at": "🇦🇹", "se": "🇸🇪", "no": "🇳🇴", "dk": "🇩🇰",
    "fi": "🇫🇮", "ie": "🇮🇪", "pl": "🇵🇱", "cz": "🇨🇿",
    "sk": "🇸🇰", "hu": "🇭🇺", "ro": "🇷🇴", "bg": "🇧🇬",
    "gr": "🇬🇷", "tr": "🇹🇷", "ua": "🇺🇦", "ru": "🇷🇺",
    "rs": "🇷🇸", "hr": "🇭🇷", "si": "🇸🇮",
    "ae": "🇦🇪", "sa": "🇸🇦", "qa": "🇶🇦",
    "in": "🇮🇳", "pk": "🇵🇰",
    "sg": "🇸🇬", "my": "🇲🇾",
    "jp": "🇯🇵", "kr": "🇰🇷", "cn": "🇨🇳",
    "za": "🇿🇦", "eg": "🇪🇬",
    "br": "🇧🇷", "ar": "🇦🇷", "mx": "🇲🇽",
    "int": "🌍", "global": "🌍",
}

# ---------------------------
# 🧠 CHANNEL → EPG MAPPING
# ---------------------------
def map_channel(clean, code):

    # US CORE
    if clean in ["abc", "cbs", "nbc", "fox"]:
        return f"{clean}.us"

    if "cnn" in clean:
        return "cnn.us"
    if "cnbc" in clean:
        return "cnbc.us"
    if "fox news" in clean:
        return "foxnews.us"

    # ESPN
    if "espn deportes" in clean:
        return "espndeportes.us"
    if "espn 2" in clean:
        return "espn2.us"
    if "espn news" in clean:
        return "espnnews.us"
    if "espn u" in clean:
        return "espnu.us"
    if "espn" in clean:
        return "espn.us"

    # DAZN
    if "dazn" in clean:
        if "1" in clean:
            return "dazn1.de"
        if "2" in clean:
            return "dazn2.de"
        if "laliga" in clean:
            return "daznlaliga.es"
        if "italy" in clean or code == "it":
            return "dazn.it"
        return "dazn1.de"

    # SKY
    if "sky sports" in clean:
        if "main event" in clean:
            return "skysportsmainevent.uk"
        if "premier league" in clean:
            return "skysportspremierleague.uk"
        if "football" in clean:
            return "skysportsfootball.uk"
        if "cricket" in clean:
            return "skysportscricket.uk"
        if "f1" in clean:
            return "skysportsf1.uk"
        return "skysportsmainevent.uk"

    # MOVISTAR
    if "movistar" in clean:
        if "laliga" in clean:
            return "movistarlaliga.es"
        if "champions" in clean:
            return "movistarchampionsleague.es"
        return "movistardeportes.es"

    # RAI
    if "rai 1" in clean:
        return "rai1.it"
    if "rai 2" in clean:
        return "rai2.it"
    if "rai 3" in clean:
        return "rai3.it"
    if "rai sport" in clean:
        return "raisport.it"

    # ZIGGO
    if "ziggo sport" in clean:
        if "select" in clean:
            return "ziggosportselect.nl"
        return "ziggosport.nl"

    # SPORT TV
    if "sport tv" in clean:
        if "1" in clean:
            return "sporttv1.pt"
        if "2" in clean:
            return "sporttv2.pt"
        if "3" in clean:
            return "sporttv3.pt"
        if "4" in clean:
            return "sporttv4.pt"
        if "5" in clean:
            return "sporttv5.pt"
        return "sporttv1.pt"

    # beIN
    if "bein" in clean:
        if "2" in clean:
            return "beinsports2.qa"
        if "3" in clean:
            return "beinsports3.qa"
        return "beinsports1.qa"

    # ASTRO (EVENT)
    if "astro cricket" in clean:
        return "willow.us"
    if "astro football" in clean:
        return "skysportsfootball.uk"
    if "astro" in clean:
        return "skysportsmainevent.uk"

    # PEACOCK
    if "peacock event" in clean:
        return "nbc.us"

    # FALLBACK
    base = clean.replace(" ", ".")
    return f"{base}.{code}" if code else base


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
# EXTRACTOR
# ---------------------------
def get_m3u8_url(channel_url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": REFERER
    }

    try:
        response = requests.get(channel_url, headers=headers, timeout=15)
        html = response.text

        m3u8 = re.search(r'https?://[^"\']+\.m3u8[^"\']*', html)
        if m3u8:
            return m3u8.group(0)

    except:
        pass

    return None


# ---------------------------
# CHANNELS API
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

        return [
            {
                "name": ch.get("name"),
                "code": ch.get("code"),
                "logo": ch.get("image"),
                "stream_url": ch.get("url"),
                "category": ch.get("category", "Live TV")
            }
            for ch in data if ch.get("status") == "online"
        ]

    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []


# ---------------------------
# MAIN
# ---------------------------
def main():
    channels = get_channels()

    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for ch in channels:
            raw_name = ch.get("name") or ""
            code = (ch.get("code") or "").lower()

            clean = raw_name.lower()
            clean = re.sub(r'[^a-z0-9 ]', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()

            tvg_id = map_channel(clean, code)

            flag = FLAG_MAP.get(code, "🏳️")
            name = f"{flag} {raw_name}"

            m3u8 = get_m3u8_url(ch["stream_url"])
            if not m3u8:
                continue

            proxy_url = PROXY + urllib.parse.quote(m3u8, safe='')

            f.write(
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{raw_name}" '
                f'tvg-logo="{ch["logo"]}" group-title="{ch["category"]}",{name}\n'
            )
            f.write(f'#EXTVLCOPT:http-referrer={REFERER}\n')
            f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n')
            f.write(proxy_url + "\n")


if __name__ == "__main__":
    main()
