import json
import subprocess
import os
import sys
import logging
from glob import glob

# ==========================================
# 設定
# ==========================================
JSON_FILE = 'list_memberonly.json'
COOKIES_FILE = 'youtube.com_cookies.txt'
OUTPUT_DIR = 'video'
LOG_DIR = 'log'
ERROR_LOG = os.path.join(LOG_DIR, 'download_error.log')
VERIFY_LOG = os.path.join(LOG_DIR, 'verify.log')
# ==========================================

# ディレクトリ準備
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# エラーロガーの設定
err_logger = logging.getLogger('error')
err_logger.setLevel(logging.ERROR)
fh = logging.FileHandler(ERROR_LOG, encoding='utf-8')
fh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
err_logger.addHandler(fh)

def verify_single_download(video_id, title):
    """1動画ごとに存在確認とffprobe(映像/音声/時間)チェック、サムネ/チャットの確認を行う"""

    all_files = os.listdir(OUTPUT_DIR)

    related_files = [f for f in all_files if f"[{video_id}]" in f]

    video_files = [f for f in related_files if f.endswith(('.mp4', '.mkv', '.webm'))]
    chat_files = [f for f in related_files if f.endswith('.live_chat.json')]
    thumb_files = [f for f in related_files if f.endswith(('.webp', '.jpg', '.jpeg', '.png'))]

    with open(VERIFY_LOG, 'a', encoding='utf-8') as vf:
        vf.write(f"\n--- 検証: {video_id} ({title}) ---\n")

        # 1. 動画ファイルの検証
        if not video_files:
            vf.write(f"[MISSING] 動画ファイルが見つかりません\n")
            print(f"  -> \033[31m[動画エラー]\033[0m ファイルが存在しません。")
        else:
            for vfile in video_files:
                vfile_path = os.path.join(OUTPUT_DIR, vfile)
                size_mb = os.path.getsize(vfile_path) / (1024 * 1024)

                cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    vfile_path
                ]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        probe_data = json.loads(res.stdout)

                        duration = float(probe_data.get('format', {}).get('duration', 0))
                        streams = probe_data.get('streams', [])
                        has_video = any(s.get('codec_type') == 'video' for s in streams)
                        has_audio = any(s.get('codec_type') == 'audio' for s in streams)

                        status_msgs = []
                        status_msgs.append(f"時間: {duration:.1f}秒" if duration > 0 else "時間: 取得失敗")
                        status_msgs.append("映像: OK" if has_video else "映像: 無し")
                        status_msgs.append("音声: OK" if has_audio else "音声: 無し")

                        if duration > 0 and has_video and has_audio:
                            vf.write(f"[OK] 動画: {vfile} (サイズ: {size_mb:.2f}MB, {', '.join(status_msgs)})\n")
                            print(f"  -> \033[32m[動画OK]\033[0m {size_mb:.2f}MB / {duration:.1f}sec (映像有/音声有)")
                        else:
                            vf.write(f"[WARNING] 動画: {vfile} (サイズ: {size_mb:.2f}MB, {', '.join(status_msgs)})\n")
                            print(f"  -> \033[33m[動画警告]\033[0m 映像または音声が欠損、あるいは時間が不正です。")
                    else:
                        vf.write(f"[CORRUPT] 動画: {vfile} (ffprobeエラー: {res.stderr})\n")
                        print(f"  -> \033[31m[動画エラー]\033[0m ffprobeの実行に失敗しました。")
                except Exception as e:
                    vf.write(f"[ERROR] 動画: {vfile} (検証例外: {str(e)})\n")
                    print(f"  -> \033[31m[動画エラー]\033[0m 検証中に例外が発生しました。")

        # 2. チャットファイルの検証
        if not chat_files:
            vf.write(f"[INFO] チャットファイル(.live_chat.json)無し\n")
            # 通常アップロード動画の場合はチャットが無いのが正常なため、警告色(黄色)にします
            print(f"  -> \033[33m[チャット無]\033[0m チャットアーカイブが存在しません。")
        else:
            for cfile in chat_files:
                cfile_path = os.path.join(OUTPUT_DIR, cfile)
                size_kb = os.path.getsize(cfile_path) / 1024
                vf.write(f"[OK] チャット: {cfile} (サイズ: {size_kb:.2f}KB)\n")
                print(f"  -> \033[36m[チャットOK]\033[0m {size_kb:.2f}KB")

        # 3. サムネイルファイルの検証
        if not thumb_files:
            vf.write(f"[MISSING] サムネイルファイル無し\n")
            print(f"  -> \033[33m[サムネ無]\033[0m サムネイルファイルが存在しません。")
        else:
            for tfile in thumb_files:
                tfile_path = os.path.join(OUTPUT_DIR, tfile)
                size_kb = os.path.getsize(tfile_path) / 1024
                vf.write(f"[OK] サムネ: {tfile} (サイズ: {size_kb:.2f}KB)\n")
                print(f"  -> \033[36m[サムネOK]\033[0m {size_kb:.2f}KB")

def download_video(video):
    video_id = video['videoId']
    title = video.get('title', 'Unknown')
    url = f"https://youtu.be/{video_id}"

    cmd = [
        "yt-dlp",
        "--newline",  # Python側でバッファを詰まらせず1行ずつパースするために必須
        "-o", f"{OUTPUT_DIR}/%(upload_date)s_%(title).190B_[%(id)s].%(ext)s",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "--add-metadata",
        "--embed-thumbnail",
        "--write-thumbnail",
        "--write-subs",
        "--sub-langs", "live_chat,ja", 
        "--cookies", COOKIES_FILE,
        url
    ]

    print(f"\n[*] ダウンロード開始: {title} ({video_id})")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        error_lines = []

        for line in process.stdout:
            if "[download]" in line and "ETA" in line:
                sys.stdout.write(f"\r\033[K  -> {line.strip()}")
                sys.stdout.flush()
            elif line.startswith("ERROR:") or line.startswith("WARNING:"):
                error_lines.append(line.strip())

        process.wait()
        print()

        if process.returncode != 0:
            error_msg = "\n".join(error_lines)
            err_logger.error(f"[{video_id}] ダウンロード失敗 (code {process.returncode}):\n{error_msg}")
            print(f"  -> \033[31m[エラー]\033[0m ダウンロードに失敗しました。(詳細は {ERROR_LOG} を確認)")
        else:
            verify_single_download(video_id, title)

    except KeyboardInterrupt:
        process.kill()
        print("\n  -> [中断] SIGINTを受け取りました。プロセスを停止します。")
        sys.exit(1)
    except Exception as e:
        err_logger.error(f"[{video_id}] 実行時例外: {str(e)}")
        print(f"  -> \033[31m[例外]\033[0m プロセス実行中にエラーが発生しました。")

def main():
    if not os.path.exists(JSON_FILE):
        print(f"エラー: {JSON_FILE} が見つかりません。")
        return

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        videos = json.load(f)

    with open(VERIFY_LOG, 'a', encoding='utf-8') as vf:
        vf.write(f"\n=== 実行開始: {os.path.basename(__file__)} ===\n")

    print(f"--- 全 {len(videos)} 件の処理を開始します ---")
    for video in videos:
        download_video(video)

    print(f"\nすべての処理が完了しました。")
    print(f"エラーログ: {ERROR_LOG}")
    print(f"検証ログ: {VERIFY_LOG}")

if __name__ == '__main__':
    main()
