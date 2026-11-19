from flask import Flask, Response
import requests

app = Flask(__name__)

DRIVE_OTTPLUS_URL = "https://drive.usercontent.google.com/u/0/uc?id=1SJi5LT5bQ1ZHT5eYQM3VOYuNB6U-mYCB&export=download"

PLAYLISTS = {
    "ottplus": DRIVE_OTTPLUS_URL,
}

def fetch_text(url):
    res = requests.get(url, timeout=20, allow_redirects=True)
    res.raise_for_status()
    return res.text

@app.route("/")
@app.route("/ottplus")
def show_ottplus():
    try:
        content = fetch_text(PLAYLISTS["ottplus"])
        return Response(content, mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return Response(f"Failed to load playlist from Google Drive: {e}", status=502, mimetype="text/plain; charset=utf-8")

@app.route("/<name>")
def serve_by_name(name):
    key = name.lower()
    if key not in PLAYLISTS:
        available = ", ".join(f"/{k}" for k in PLAYLISTS.keys())
        return Response(f"Playlist not found. Available routes: {available}", status=404, mimetype="text/plain; charset=utf-8")
    try:
        content = fetch_text(PLAYLISTS[key])
        return Response(content, mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return Response(f"Failed to load playlist '{key}': {e}", status=502, mimetype="text/plain; charset=utf-8")

if __name__ == "__main__":
    app.run(debug=True)
