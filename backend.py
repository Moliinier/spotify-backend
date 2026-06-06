#!/usr/bin/env python3
# ╔══════════════════════════════════════════════╗
# ║       SPOTIFY MUSIC PLAYER - BACKEND         ║
# ║       Flask + yt-dlp                         ║
# ║       Puerto: 5000                           ║
# ╚══════════════════════════════════════════════╝

# INSTALACIÓN:
#   pip install flask yt-dlp flask-cors
#
# USO:
#   python backend.py
#
# Luego en el script Lua cambia:
#   local BACKEND_URL = "http://TU-IP:5000"
# por tu IP local, ejemplo:
#   local BACKEND_URL = "http://192.168.1.10:5000"

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback

app = Flask(__name__)
CORS(app)  # Permite requests desde cualquier origen

# ══════════════════════════════════════
# OPCIONES BASE DE YT-DLP
# ══════════════════════════════════════
BASE_OPTS = {
    "quiet":            True,
    "no_warnings":      True,
    "extract_flat":     False,
    "noplaylist":       True,
    "skip_download":    True,
    "format":           "bestaudio/best",
    "cookiesfrombrowser": None,  # Opcional: ("chrome",) si hay bloqueos
}

# ══════════════════════════════════════
# RUTA: /search?q=CONSULTA
# Devuelve lista de canciones encontradas
# ══════════════════════════════════════
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parametro 'q' requerido"}), 400

    # Si es una URL directa de YouTube, extraer info directamente
    is_url = query.startswith("http://") or query.startswith("https://")

    search_query = query if is_url else f"ytsearch5:{query}"

    opts = {**BASE_OPTS, "extract_flat": is_url is False}

    results = []

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

            entries = []
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
            else:
                entries = [info]

            for entry in entries[:5]:  # Máximo 5 resultados
                video_id = entry.get("id") or entry.get("url", "")
                title    = entry.get("title", "Sin título")
                duration = entry.get("duration")
                uploader = entry.get("uploader") or entry.get("channel", "YouTube")

                # Formatear duración
                if duration:
                    mins = int(duration) // 60
                    secs = int(duration) % 60
                    duration_str = f"{mins}:{secs:02d}"
                else:
                    duration_str = "?"

                # Construir URL de audio directo
                audio_url = get_audio_url(video_id if not is_url else query)

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

    if not results:
        return jsonify([]), 200

    return jsonify(results), 200


# ══════════════════════════════════════
# RUTA: /audio?id=VIDEO_ID
# Devuelve la URL de audio directa de un video
# ══════════════════════════════════════
@app.route("/audio")
def audio():
    video_id = request.args.get("id", "").strip()
    if not video_id:
        return jsonify({"error": "Parametro 'id' requerido"}), 400

    url = f"https://www.youtube.com/watch?v={video_id}"
    audio_url = get_audio_url(url)

    if not audio_url:
        return jsonify({"error": "No se pudo obtener el audio"}), 404

    return jsonify({"audioUrl": audio_url}), 200


# ══════════════════════════════════════
# RUTA: /ping
# Para verificar que el servidor está vivo
# ══════════════════════════════════════
@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Backend activo"}), 200


# ══════════════════════════════════════
# HELPER: obtener URL de audio directo
# ══════════════════════════════════════
def get_audio_url(url_or_id):
    """
    Dado un ID o URL de YouTube, devuelve la URL directa
    del stream de audio (compatible con Roblox Sound).
    """
    # Si es solo un ID, construir la URL
    if not url_or_id.startswith("http"):
        url_or_id = f"https://www.youtube.com/watch?v={url_or_id}"

    opts = {
        **BASE_OPTS,
        "extract_flat": False,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_or_id, download=False)

            # Buscar el mejor formato de audio
            formats = info.get("formats", [])
            audio_formats = [
                f for f in formats
                if f.get("acodec") != "none"
                and f.get("vcodec") == "none"
                and f.get("url")
            ]

            if audio_formats:
                # Ordenar por calidad (abr = audio bitrate)
                audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
                return audio_formats[0]["url"]

            # Fallback: usar la URL directa del info
            if info.get("url"):
                return info["url"]

    except Exception as e:
        print(f"[ERROR get_audio_url] {url_or_id} -> {e}")

    return None


# ══════════════════════════════════════
# INICIO DEL SERVIDOR
# ══════════════════════════════════════
if __name__ == "__main__":
    print("╔══════════════════════════════════════╗")
    print("║   Spotify Music Player - Backend     ║")
    print("║   Flask + yt-dlp  |  Puerto 5000     ║")
    print("╚══════════════════════════════════════╝")
    print()
    print("Rutas disponibles:")
    print("  GET /ping              -> Estado del servidor")
    print("  GET /search?q=CANCION  -> Buscar canciones")
    print("  GET /audio?id=VIDEO_ID -> URL de audio directa")
    print()
    print("Iniciando servidor en http://0.0.0.0:5000 ...")
    print()

    # host="0.0.0.0" para que sea accesible desde la red local
    app.run(host="0.0.0.0", port=5000, debug=False)
