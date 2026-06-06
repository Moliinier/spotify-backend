#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback
import os

app = Flask(__name__)
CORS(app)

# YouTube Data API v3 key
YT_API_KEY = os.environ.get("YT_API_KEY", "AIzaSyAf3wfUwfdc-BT95zFWegF_KMiXTtpE5t8")

# Invidious para obtener el audio (URLs directas)
INVIDIOUS_INSTANCES = [
    "https://invidious.privacydev.net",
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.fdn.fr",
    "https://iv.datura.network",
]

def inv_get(path):
    for instance in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(f"{instance}{path}", timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[WARN] {instance} falló: {e}")
    return None


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parametro 'q' requerido"}), 400

    results = []

    try:
        # Buscar con YouTube Data API v3 (oficial, sin bloqueos)
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
        print(f"[YT API] status: {r.status_code}")
        data = r.json()

        if "error" in data:
            print(f"[YT API ERROR] {data['error']}")
            return jsonify({"error": data["error"]["message"]}), 500

        items = data.get("items", [])
        print(f"[DEBUG] Videos encontrados: {len(items)}")

        # Obtener duraciones con videos.list
        video_ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
        dur_r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "contentDetails",
                "id": ",".join(video_ids),
                "key": YT_API_KEY,
            },
            timeout=10
        )
        durations = {}
        for v in dur_r.json().get("items", []):
            vid = v["id"]
            iso = v["contentDetails"]["duration"]  # PT3M45S
            import re
            m = re.search(r"PT(?:(\d+)M)?(?:(\d+)S)?", iso)
            mins = int(m.group(1) or 0)
            secs = int(m.group(2) or 0)
            durations[vid] = f"{mins}:{secs:02d}"

        for item in items:
            video_id = item["id"]["videoId"]
            title    = item["snippet"]["title"]
            uploader = item["snippet"]["channelTitle"]
            duration_str = durations.get(video_id, "?")

            audio_url = get_audio_url(video_id)

            if audio_url:
                results.append({
                    "title":    title,
                    "artist":   uploader,
                    "duration": duration_str,
                    "videoId":  video_id,
                    "audioUrl": audio_url,
                })

    except Exception as e:
        print(f"[ERROR /search] {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify(results), 200


@app.route("/audio")
def audio():
    video_id = request.args.get("id", "").strip()
    if not video_id:
        return jsonify({"error": "Parametro 'id' requerido"}), 400

    audio_url = get_audio_url(video_id)
    if not audio_url:
        return jsonify({"error": "No se pudo obtener el audio"}), 404

    return jsonify({"audioUrl": audio_url}), 200


@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Backend activo"}), 200


def get_audio_url(video_id):
    try:
        data = inv_get(f"/api/v1/videos/{video_id}?fields=adaptiveFormats,formatStreams")
        if not data:
            return None

        formats = data.get("adaptiveFormats", [])
        audio_formats = [
            f for f in formats
            if "audio" in f.get("type", "") and f.get("url")
        ]

        if audio_formats:
            audio_formats.sort(key=lambda f: f.get("bitrate", 0), reverse=True)
            return audio_formats[0]["url"]

        streams = data.get("formatStreams", [])
        if streams:
            return streams[0].get("url")

    except Exception as e:
        print(f"[ERROR get_audio_url] {video_id} -> {e}")

    return None


if __name__ == "__main__":
    print("Backend iniciando en http://0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
