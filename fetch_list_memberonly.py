import json
import urllib.request
import urllib.parse
import ssl
import subprocess
import os

# ==========================================
# 設定
# ==========================================
API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
HANDLE = '@KulakuLie'
COOKIES_FILE = 'youtube.com_cookies.txt'
OUTPUT_MEMBER = 'list_memberonly.json'
# ==========================================

def get_memberonly_playlist_id(api_key, handle):
    """ハンドル名からチャンネルIDを取得し、メン限プレイリスト(UUMO)IDを生成"""
    safe_handle = urllib.parse.quote(handle)
    url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={safe_handle}&key={api_key}"

    req = urllib.request.Request(url)
    context = ssl.create_default_context()
    with urllib.request.urlopen(req, context=context) as res:
        data = json.loads(res.read())
        if 'items' not in data or len(data['items']) == 0:
            raise Exception(f"チャンネル {handle} が見つかりませんでした。")

        channel_id = data['items'][0]['id']
        uumo_id = f"UUMO{channel_id[2:]}"
        return uumo_id

def fetch_memberonly_videos_ytdlp(playlist_id, cookies_file):
    """yt-dlpを使用してメン限プレイリストを全件取得"""
    if not os.path.exists(cookies_file):
        raise FileNotFoundError(f"{cookies_file} が見つかりません。")

    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--cookies", cookies_file,
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    videos = []

    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        info = json.loads(line)

        raw_date = info.get('upload_date')
        if raw_date and len(raw_date) == 8:
            published_at = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}T00:00:00Z"
        else:
            published_at = "1970-01-01T00:00:00Z"

        videos.append({
            "publishedAt": published_at,
            "title": info.get('title', 'Unknown Title'),
            "videoId": info.get('id')
        })

    videos.sort(key=lambda x: x['publishedAt'], reverse=True)
    return videos

def main():
    try:
        print(f"【{HANDLE}】 のメン限プレイリストIDを取得中...")
        uumo_id = get_memberonly_playlist_id(API_KEY, HANDLE)
        print(f"-> メン限プレイリストID: {uumo_id}")

        print(f"yt-dlpとCookieを使用してメン限動画を取得中...")
        member_videos = fetch_memberonly_videos_ytdlp(uumo_id, COOKIES_FILE)

        with open(OUTPUT_MEMBER, 'w', encoding='utf-8') as f:
            json.dump(member_videos, f, ensure_ascii=False, indent=2)

        print(f"完了: {OUTPUT_MEMBER} に {len(member_videos)} 件保存しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
