import json
import urllib.request
import urllib.parse
import ssl
import subprocess
import os
import http.cookiejar
import re
from datetime import datetime, timezone

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

def get_publish_date(video_id, cookiejar):
    """動画ページにアクセスしてHTMLから公開日と正確な時刻を抽出する"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(url)

    # 弾かれないように一般的なUser-Agentを設定
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    cookiejar.add_cookie_header(req)

    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=context) as res:
            html = res.read().decode('utf-8')

            date_str = None

            # パターン1: metaタグから抽出
            match = re.search(r'<meta itemprop="datePublished" content="([^"]+)">', html)
            if match:
                date_str = match.group(1)
            else:
                # パターン2: JSONデータ内から抽出
                match = re.search(r'"publishDate":"([^"]+)"', html)
                if match:
                    date_str = match.group(1)

            if date_str:
                # タイムゾーン付きの時刻 (例: 2026-05-25T14:05:40-07:00) が取れた場合
                if 'T' in date_str:
                    try:
                        # 文字列を日時に変換し、APIの標準仕様であるUTC(協定世界時)に合わせてZフォーマットにする
                        dt = datetime.fromisoformat(date_str)
                        dt_utc = dt.astimezone(timezone.utc)
                        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except ValueError:
                        return date_str # 万が一変換に失敗した場合はそのまま記録

                # 万が一、日付のみ (例: 2026-05-25) しか取れなかった場合のフェイルセーフ
                elif len(date_str) == 10:
                    return f"{date_str}T00:00:00Z"

    except Exception:
        pass

    return "1970-01-01T00:00:00Z"

def fetch_memberonly_videos(playlist_id, cookies_file):
    """yt-dlpでIDを高速取得し、日時はPythonで個別取得する"""
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

    print("yt-dlpでプレイリストの基本情報(動画ID・タイトル)を取得中...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    # CookieファイルをPython用に読み込む
    cj = http.cookiejar.MozillaCookieJar(cookies_file)
    cj.load(ignore_discard=True, ignore_expires=True)

    lines = [line for line in result.stdout.strip().split('\n') if line]
    total = len(lines)
    print(f"\n{total} 件の動画が見つかりました。各動画の正確な日時情報を取得します...")

    videos = []
    for i, line in enumerate(lines):
        info = json.loads(line)
        video_id = info.get('id')
        title = info.get('title', 'Unknown Title')

        # PythonでHTMLから日時だけをスクレイピング (yt-dlpの解析を待つより圧倒的に速い)
        published_at = get_publish_date(video_id, cj)

        videos.append({
            "publishedAt": published_at,
            "title": title,
            "videoId": video_id
        })

        # 進捗を表示
        print(f"[{i+1}/{total}] 完了: {published_at[:10]} | {title}")

    # 日付の降順でソート
    videos.sort(key=lambda x: x['publishedAt'], reverse=True)
    return videos

def main():
    try:
        print(f"【{HANDLE}】 のメン限プレイリストIDを取得中...")
        uumo_id = get_memberonly_playlist_id(API_KEY, HANDLE)
        print(f"-> メン限プレイリストID: {uumo_id}\n")

        member_videos = fetch_memberonly_videos(uumo_id, COOKIES_FILE)

        with open(OUTPUT_MEMBER, 'w', encoding='utf-8') as f:
            json.dump(member_videos, f, ensure_ascii=False, indent=2)

        print(f"\n完了: {OUTPUT_MEMBER} に {len(member_videos)} 件保存しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
