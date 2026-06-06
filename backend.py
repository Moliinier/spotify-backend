#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

# Instancias de Invidious (API alternativa de YouTube, más estable)
INVIDIOUS_INSTANCES = [
    "https://invidious.privacydev.net",
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.fdn.fr",
    "https://iv.datura.network",
]

def inv_get(path):
    """Hace GET a la primera instancia de Invidious que responda."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(f"{instance}{path}", timeout=10)
            print(f"[INV] {instance}{path} -> {r.status_code}")
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
        data = inv_get(f"/api/v1/search?q={requests.utils.quote(query)}&type=video&fields=videoId,title,author,lengthSeconds")

        if not data:
            return jsonify({"error": "Invidious no respondió"}), 500

        print(f"[DEBUG] Resultados: {len(data)}")

        for item in data[:5]:
            video_id = item.get("videoId", "")
            title    = item.get("title", "Sin título")
            uploader = item.get("author", "YouTube")
            duration = item.get("lengthSeconds", 0)

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
    """Obtiene URL de audio via Invidious."""
    try:
        data = inv_get(f"/api/v1/videos/{video_id}?fields=adaptiveFormats,formatStreams")
        if not data:
            return None

        # Buscar en adaptiveFormats (solo audio)
        formats = data.get("adaptiveFormats", [])
        audio_formats = [
            f for f in formats
            if "audio" in f.get("type", "") and f.get("url")
        ]

        if audio_formats:
            # Ordenar por bitrate
            audio_formats.sort(key=lambda f: f.get("bitrate", 0), reverse=True)
            print(f"[DEBUG] Audio URL encontrada para {video_id}")
            return audio_formats[0]["url"]

        # Fallback: formatStreams (video+audio combinado)
        streams = data.get("formatStreams", [])
        if streams:
            return streams[0].get("url")

    except Exception as e:
        print(f"[ERROR get_audio_url] {video_id} -> {e}")

    return None


if __name__ == "__main__":
    print("Backend iniciando en http://0.0.0.0:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
