from flask import Flask, Response, request, jsonify
import json
import os
import re
import requests

app = Flask(__name__)

STORE_FILE = os.environ.get("PLAYLIST_STORE_FILE", "/tmp/playlists.json")

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

# Map short IDs to Google Drive file IDs or full URLs
PLAYLIST_IDS = {
    "ottplus": "1SJi5LT5bQ1ZHT5eYQM3VOYuNB6U-mYCB",
}


def extract_file_id_or_url(value: str) -> str:
    value = value.strip()
    match = re.search(r"(?:drive\.google\.com/file/d/|id=)([a-zA-Z0-9_-]+)", value)
    if match:
        return match.group(1)
    return value


def get_all_sources() -> dict:
    sources = dict(PLAYLIST_IDS)
    env_json = os.environ.get("PLAYLISTS_JSON")
    if env_json:
        try:
            parsed = json.loads(env_json)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                        sources[k.strip().lower()] = extract_file_id_or_url(v)
        except Exception:
            pass

    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    for k, v in saved.items():
                        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                            sources[k.strip().lower()] = extract_file_id_or_url(v)
        except Exception:
            pass

    return sources


def save_sources(sources: dict) -> None:
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(sources, f, indent=2)
    except Exception:
        pass


def html_response(body: str, status: int = 200) -> Response:
    return Response(
        body,
        status=status,
        mimetype="text/html",
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Content-Disposition": "inline",
        },
    )


def fetch_drive_content(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        direct_url = source
    else:
        direct_url = f"https://drive.usercontent.google.com/u/0/uc?id={source}&export=download"

    res = requests.get(
        direct_url,
        headers={"User-Agent": CHROME_USER_AGENT},
        timeout=20,
        allow_redirects=True,
    )
    http_code = res.status_code

    if http_code != 200:
        return (
            f"#EXTM3U\n#ERROR: Google Drive denied access (HTTP Code {http_code}). "
            "Check if the file is public."
        )

    return res.text


@app.route("/")
def index():
    sources = get_all_sources()
    requested_id = (request.args.get("id") or "").strip().lower()

    if not requested_id:
        requested_id = "ottplus" if "ottplus" in sources else next(iter(sources), "")

    if not requested_id or requested_id not in sources:
        available = ", ".join(f"?id={k}" for k in sources.keys())
        return html_response(
            f"#EXTM3U\n#ERROR: Playlist not found. Available: {available}",
            status=404,
        )

    data = fetch_drive_content(sources[requested_id])
    return html_response(data, status=200)


@app.route("/add", methods=["GET", "POST"])
def add_source():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form or {}
        name = str(payload.get("name", "")).strip().lower()
        target = str(payload.get("url") or payload.get("id") or "").strip()
    else:
        name = str(request.args.get("name", "")).strip().lower()
        target = str(request.args.get("url") or request.args.get("id") or "").strip()

    if not name or not target:
        return jsonify({"error": "Both 'name' and 'url' (or 'id') are required."}), 400

    sources = get_all_sources()
    sources[name] = extract_file_id_or_url(target)
    save_sources(sources)

    return jsonify({"status": "added", "name": name, "view": f"/?id={name}"}), 201


if __name__ == "__main__":
    app.run(debug=True)
