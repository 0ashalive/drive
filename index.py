from flask import Flask, Response
import requests

app = Flask(__name__)

# Add all your Google Drive download links or M3U URLs here
PLAYLISTS = {
    "ottplus": "https://drive.usercontent.google.com/u/0/uc?id=1SJi5LT5bQ1ZHT5eYQM3VOYuNB6U-mYCB&export=download",
    "sports": "https://drive.usercontent.google.com/u/0/uc?id=YOUR_SECOND_FILE_ID&export=download",
    "movies": "https://drive.usercontent.google.com/u/0/uc?id=YOUR_THIRD_FILE_ID&export=download",
}

@app.route('/')
def home():
    keys = "\n".join(f"/{k}" for k in PLAYLISTS)
    return Response(f"Available routes:\n{keys}\n/all\n", mimetype='text/plain; charset=utf-8')

@app.route('/<name>')
def serve_playlist(name):
    url = PLAYLISTS.get(name)
    if not url:
        return Response("Playlist not found", status=404, mimetype='text/plain; charset=utf-8')
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return Response(res.text, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        return Response(f"Error fetching {name}: {str(e)}", status=500, mimetype='text/plain; charset=utf-8')

@app.route('/all')
def serve_all():
    combined = ["#EXTM3U"]
    for name, url in PLAYLISTS.items():
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            lines = [line for line in res.text.splitlines() if not line.strip().startswith("#EXTM3U")]
            combined.extend(lines)
        except Exception:
            continue
    return Response("\n".join(combined), mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    app.run()
  
