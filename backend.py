#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback

app = Flask(__name__)
CORS(app)

SEARCH_OPTS = {
    "quiet":         True,
    "no_warnings":   True,
    "noplaylist":    True,
    "skip_download": True,
    "extract_flat":  True,  # Solo metadatos, sin extraer audio aún
}

AUDIO_OPTS = {
    "quiet":         True,
    "no_warnings":   True,
    "noplaylist":    True,
    "skip_download": True,
    "extract_flat":  False,
    "format":        "bestaudio[ext=m4a]/bestaudio/best",
    "extractor_args": {
        "youtube": {
            "player_client": ["ios"],
        }
    },
}

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parametro 'q' requerido"}), 400

    results = []

    try:
        # Paso 1: buscar videos (solo metadatos)
        with yt_dlp.YoutubeDL(SEARCH_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            entries = [e for e in info.get("entries", []) if e]

        # Paso 2: para cada video, obtener URL de audio
        for entry in entries[:5]:
            video_id = entry.get("id", "")
            title    = entry.get("title", "Sin título")
            duration = entry.get("duration")
            uploader = entry.get("uploader") or entry.get("channel", "YouTube")

            if not video_id:
                continue

            if duration:
                mins = int(duration) // 60
                secs = int(duration) % 60
                duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "?"

            audio_url = get_audio_url(f"https://www.youtube.com/watch?v={video_id}")

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

    audio_url = get_audio_url(f"https://www.youtube.com/watch?v={video_id}")
    if not audio_url:
        return jsonify({"error": "No se pudo obtener el audio"}), 404

    return jsonify({"audioUrl": audio_url}), 200


@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Backend activo"}), 200


def get_audio_url(url):
    try:
        with yt_dlp.YoutubeDL(AUDIO_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = info.get("formats", [])
            audio_formats = [
                f for f in formats
                if f.get("acodec") != "none"
                and f.get("vcodec") == "none"
                and f.get("url")
            ]

            if audio_formats:
                audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
                return audio_formats[0]["url"]

            if info.get("url"):
                return info["url"]

    except Exception as e:
        print(f"[ERROR get_audio_url] {url} -> {e}")

    return None


if __name__ == "__main__":
    print("Backend iniciando en http://0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
