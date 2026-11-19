from flask import Flask, Response, request, jsonify
import json
import os
import re
import requests

app = Flask(__name__)

STORE_FILE = os.environ.get("PLAYLIST_STORE_FILE", "/tmp/playlists.json")

DEFAULT_PLAYLISTS = {
    "ottplus": "https://drive.usercontent.google.com/u/0/uc?id=1SJi5LT5bQ1ZHT5eYQM3VOYuNB6U-mYCB&export=download",
}


def normalize_drive_url(url: str) -> str:
    url = url.strip()
    match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return f"https://drive.usercontent.google.com/u/0/uc?id={match.group(1)}&export=download"
    return url


def load_playlists() -> dict:
    data = dict(DEFAULT_PLAYLISTS)
    env_json = os.environ.get("PLAYLISTS_JSON")
    if env_json:
        try:
            parsed = json.loads(env_json)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                        data[k.strip().lower()] = normalize_drive_url(v)
        except Exception:
            pass

    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    for k, v in saved.items():
                        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                            data[k.strip().lower()] = normalize_drive_url(v)
        except Exception:
            pass

    return data


def save_playlists(playlists: dict) -> None:
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(playlists, f, indent=2)
    except Exception:
        pass


def fetch_m3u_data(url: str) -> str:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    res = session.get(url, headers=headers, timeout=20, allow_redirects=True)
    res.raise_for_status()

    if "text/html" in res.headers.get("Content-Type", "") and "confirm=" in res.text:
        confirm_match = re.search(r"confirm=([0-9A-Za-z_]+)", res.text)
        if confirm_match:
            sep = "&" if "?" in url else "?"
            res = session.get(f"{url}{sep}confirm={confirm_match.group(1)}", headers=headers, timeout=20, allow_redirects=True)
            res.raise_for_status()

    text = res.text.strip()
    if not text.startswith("#EXTM3U"):
        text = "#EXTM3U\n" + text
    return text + "\n"


def inline_m3u_response(text: str, status: int = 200) -> Response:
    return Response(
        text,
        status=status,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "inline"},
    )


@app.route("/")
def home():
    playlists = load_playlists()
    lines = [
        "#EXTM3U",
        "# Available M3U Endpoints:",
        *(f"#   /{name}" for name in playlists.keys()),
        "#   /all",
    ]
    return inline_m3u_response("\n".join(lines) + "\n")


@app.route("/add", methods=["GET", "POST"])
def add_playlist():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form or {}
        name = str(payload.get("name", "")).strip().lower()
        raw_url = str(payload.get("url", "")).strip()
    else:
        name = str(request.args.get("name", "")).strip().lower()
        raw_url = str(request.args.get("url", "")).strip()

    if not name or not raw_url:
        return jsonify({"error": "Both 'name' and 'url' are required."}), 400

    if not re.match(r"^[a-z0-9_-]+$", name) or name in {"add", "all"}:
        return jsonify({"error": "Invalid 'name'."}), 400

    playlists = load_playlists()
    playlists[name] = normalize_drive_url(raw_url)
    save_playlists(playlists)

    return jsonify({"status": "added", "name": name, "view_path": f"/{name}"}), 201


@app.route("/all")
def serve_all():
    playlists = load_playlists()
    merged = ["#EXTM3U"]
    for _, url in playlists.items():
        try:
            content = fetch_m3u_data(url)
            for line in content.splitlines():
                if not line.strip().startswith("#EXTM3U"):
                    merged.append(line)
        except Exception:
            continue
    return inline_m3u_response("\n".join(merged) + "\n")


@app.route("/<name>")
def serve_playlist(name):
    key = name.strip().lower()
    playlists = load_playlists()
    url = playlists.get(key)
    if not url:
        available = ", ".join(f"/{k}" for k in playlists.keys())
        return inline_m3u_response(f"#EXTM3U\n# Playlist not found. Available: {available}\n", status=404)

    try:
        content = fetch_m3u_data(url)
        return inline_m3u_response(content)
    except Exception as e:
        return inline_m3u_response(f"#EXTM3U\n# Error loading '{key}': {e}\n", status=502)


if __name__ == "__main__":
    app.run(debug=True)
