#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback
import re
import os

app = Flask(__name__)
CORS(app)

YT_API_KEY = os.environ.get("YT_API_KEY", "AIzaSyAf3wfUwfdc-BT95zFWegF_KMiXTtpE5t8")

import requests

def search_youtube(query):
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 5,
            "key": YT_API_KEY,
        },
        timeout=10
    )
    data = r.json()
    if "error" in data:
        return None, data["error"]["message"]
    
    items = [i for i in data.get("items", []) if i.get("id", {}).get("videoId")]
    video_ids = [i["id"]["videoId"] for i in items]
    
    durations = {}
    if video_ids:
        dur_r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "contentDetails", "id": ",".join(video_ids), "key": YT_API_KEY},
            timeout=10
        )
        for v in dur_r.json().get("items", []):
            vid = v["id"]
            iso = v["contentDetails"]["duration"]
            m = re.search(r"PT(?:(\d+)M)?(?:(\d+)S)?", iso)
            mins = int(m.group(1) or 0) if m else 0
            secs = int(m.group(2) or 0) if m else 0
            durations[vid] = f"{mins}:{secs:02d}"
    
    results = []
    for item in items:
        video_id = item["id"]["videoId"]
        results.append({
            "title":    item["snippet"]["title"],
            "artist":   item["snippet"]["channelTitle"],
            "duration": durations.get(video_id, "?"),
            "videoId":  video_id,
        })
    return results, None


def get_audio_url(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios"],
                "player_skip": ["webpage"],
            }
        },
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            audio = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url")]
            if audio:
                audio.sort(key=lambda f: f.get("abr") or 0, reverse=True)
                return audio[0]["url"]
            if info.get("url"):
                return info["url"]
    except Exception as e:
        print(f"[ERROR get_audio_url] {e}")
    return None


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parametro 'q' requerido"}), 400

    try:
        items, err = search_youtube(query)
        if err:
            return jsonify({"error": err}), 500

        results = []
        for item in items:
            audio_url = get_audio_url(item["videoId"])
            if audio_url:
                item["audioUrl"] = audio_url
                results.append(item)

        return jsonify(results), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/audio")
def audio():
    video_id = request.args.get("id", "").strip()
    if not video_id:
        return jsonify({"error": "Parametro 'id' requerido"}), 400
    url = get_audio_url(video_id)
    if not url:
        return jsonify({"error": "No se pudo obtener el audio"}), 404
    return jsonify({"audioUrl": url}), 200


@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Backend activo"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
