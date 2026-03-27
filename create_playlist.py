import requests
import time
import random
import re

API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

# 🔁 YOUR LOCAL PROXY
PROXY_BASE = "http://192.168.1.101:8090/proxy?url="


# -------------------------------
# Extract m3u8 from player API
# -------------------------------
def get_m3u8_url(player_url, referer):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer
    }

    r = requests.get(player_url, headers=headers, timeout=10)
    r.raise_for_status()

    # Extract m3u8 link
    match = re.search(r'(https://[^\s"]+\.m3u8[^\s"]*)', r.text)

    if match:
        return match.group(1)

    return None


# -------------------------------
# Retry wrapper (VERY IMPORTANT)
# -------------------------------
def safe_extract(url, referer):
    for attempt in range(3):
        try:
            return get_m3u8_url(url, referer)
        except Exception as e:
            print(f"Retry {attempt+1} failed: {e}")
            time.sleep(random.uniform(1, 2))
    return None


# -------------------------------
# Fetch sports data
# -------------------------------
def fetch_events():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(API_URL, headers=headers)
    r.raise_for_status()

    return r.json()


# -------------------------------
# MAIN
# -------------------------------
def main():
    data = fetch_events()

    events = data.get("cdn-live-tv", {})
    playlist = ["#EXTM3U"]

    total_channels = 0
    failed = 0

    for category, matches in events.items():

        # skip metadata keys
        if not isinstance(matches, list):
            continue

        for match in matches:
            title = f"{match.get('homeTeam')} vs {match.get('awayTeam')}"
            time_str = match.get("time", "")
            tournament = match.get("tournament", "Sports")

            channels = match.get("channels", [])

            for ch in channels:
                channel_name = ch.get("channel_name")
                stream_url = ch.get("url")
                referer = "https://edge.cdn-live.ru/"

                print(f"Processing: {title} - {channel_name}")

                # 🔥 delay to avoid ban
                time.sleep(random.uniform(1.5, 3.5))

                m3u8 = safe_extract(stream_url, referer)

                if not m3u8:
                    print(f"FAILED: {title} - {channel_name}")
                    failed += 1
                    continue

                # 🔥 encode for proxy
                proxied = PROXY_BASE + requests.utils.quote(m3u8, safe="")

                playlist.append(
                    f'#EXTINF:-1 tvg-id="{ch.get("channel_code")}" '
                    f'tvg-name="{title} [{tournament}] ({channel_name})" '
                    f'group-title="{tournament}",{title} [{tournament}] ({channel_name})'
                )

                playlist.append("#EXTVLCOPT:http-referrer=https://edge.cdn-live.ru/")
                playlist.append(proxied)

                total_channels += 1

    # -------------------------------
    # WRITE FILE
    # -------------------------------
    with open("cdn-live.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist))

    print("\n====================")
    print(f"TOTAL CHANNELS: {total_channels}")
    print(f"FAILED: {failed}")
    print("====================")


# -------------------------------
if __name__ == "__main__":
    main()
