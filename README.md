# lie_list

## Description

- `list_memberonly.json`: メンバーシップ限定のリスト
- `fetch_list_memberonly.py`: YouTube Data APIとyt-dlpを使用して最新のメン限動画リストを自動生成するPythonスクリプト
- `download_and_verify.py`: yt-dlpを使用して、JSONリストから動画本体・チャット・サムネイルを一括ダウンロードし、ffprobeでファイルの整合性チェック(検証)まで行うPythonスクリプト

## Usage of Scripts

各スクリプトの使用方法を以下に説明します。

使用するリストについては、消費ストレージ容量や掛かる時間を検討し吟味してください。
すべての動画をダウンロードした場合、`video`ディレクトリのサイズは数百GBからTBクラスになる可能性があります。
ダウンロード対象を変更したい場合は、対象のJSONファイルを直接編集してカスタマイズすることも可能です。

### Requirements

- Python 3
- git
- yt-dlp
- ffmpeg
- ffprobe
- 十分なストレージ容量

まず、このリポジトリをcloneします。WSLにて実行する場合、WSL内ではなくWindows上のディレクトリにて行うことをお勧めします。
```
git clone https://github.com/kenh0u/lie_list.git
```

yt-dlpとffmpegをインストール (Ubuntuの場合のコマンド例)

```
sudo pipx install yt-dlp
sudo apt install ffmpeg
```

メンバーシップ限定配信アーカイブをダウンロードしたい場合、またはリストを生成したい場合は、メンバーシップに加入した上で
Chrome拡張機能[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
などを使用してYouTubeのCookieを抜き取り、`youtube.com_cookies.txt`として配置してください。

### リストの生成・更新 (fetch_list_memberonly.py)

動画リストを新規取得・更新する場合に使用します。
実行前に、Google Cloud Console等で発行したYouTube Data API v3のキーをスクリプト内の `API_KEY` 変数に設定してください。（※GitHubへ公開する際はAPIキーを含めないようご注意ください）

スクリプトを実行します。
```bash
python3 fetch_list_memberonly.py
```

### ダウンロードと検証 (download_and_verify.py)

`list_memberonly.json` に記載された動画・チャット・サムネイルを一括でダウンロードし、検証を行います。
スクリプト内の `JSON_FILE` 変数をご希望のリスト名に変更した上で実行してください。

スクリプトを実行します。
```bash
python3 download_and_verify.py
```

ファイルは`video`ディレクトリ以下に保存されます。
ダウンロードエラーは `log/download_error.log` に、ffprobe等による検証結果は `log/verify.log` にそれぞれ出力・追記されます。
