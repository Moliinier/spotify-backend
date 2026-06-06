#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://piped-api.privacy.com.de",
    "https://api.piped.yt",
]

def piped_get(path):
    for instance in PIPED_INSTANCES:
        try:
            r = requests.get(f"{instance}{path}", timeout=10)
            print(f"[PIPED] {instance}{path} -> {r.status_code}")
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
        data = piped_get(f"/search?q={requests.utils.quote(query)}&filter=videos")
        
        if not data:
            print("[ERROR] Piped no respondió")
            return jsonify({"error": "Piped no respondió"}), 500

        print(f"[DEBUG] Keys en respuesta: {list(data.keys())}")
        items = data.get("items", [])
        print(f"[DEBUG] Total items: {len(items)}")
        
        if items:
            print(f"[DEBUG] Primer item: {items[0]}")

        streams = [i for i in items if i.get("type") == "stream"][:5]
        print(f"[DEBUG] Streams encontrados: {len(streams)}")

        for item in streams:
            video_id = item.get("url", "").replace("/watch?v=", "")
            title    = item.get("title", "Sin título")
            uploader = item.get("uploaderName", "YouTube")
            duration = item.get("duration", 0)

            if not video_id:
                continue

            if duration:
                mins = int(duration) // 60
                secs = int(duration) % 60
                duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "?"

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
        data = piped_get(f"/streams/{video_id}")
        if not data:
            return None

        audio_streams = data.get("audioStreams", [])
        print(f"[DEBUG] Audio streams para {video_id}: {len(audio_streams)}")
        
        if not audio_streams:
            return None

        audio_streams.sort(key=lambda s: s.get("bitrate", 0), reverse=True)
        return audio_streams[0].get("url")

    except Exception as e:
        print(f"[ERROR get_audio_url] {video_id} -> {e}")

    return None


if __name__ == "__main__":
    print("Backend iniciando en http://0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
