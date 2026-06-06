#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback
import re
import os

app = Flask(__name__)
CORS(app)

YT_API_KEY = os.environ.get("YT_API_KEY", "AIzaSyAf3wfUwfdc-BT95zFWegF_KMiXTtpE5t8")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parametro 'q' requerido"}), 400

    results = []

    try:
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
            return jsonify({"error": data["error"]["message"]}), 500

        items = [i for i in data.get("items", []) if i.get("id", {}).get("videoId")]

        video_ids = [i["id"]["videoId"] for i in items]
        durations = {}
        if video_ids:
            dur_r = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "contentDetails",
                    "id": ",".join(video_ids),
                    "key": YT_API_KEY,
                },
                timeout=10
            )
            for v in dur_r.json().get("items", []):
                vid = v["id"]
                iso = v["contentDetails"]["duration"]
                m = re.search(r"PT(?:(\d+)M)?(?:(\d+)S)?", iso)
                mins = int(m.group(1) or 0) if m else 0
                secs = int(m.group(2) or 0) if m else 0
                durations[vid] = f"{mins}:{secs:02d}"

        for item in items:
            video_id = item["id"]["videoId"]
            results.append({
                "title":    item["snippet"]["title"],
                "artist":   item["snippet"]["channelTitle"],
                "duration": durations.get(video_id, "?"),
                "videoId":  video_id,
                "audioUrl": f"https://inv.nadeko.net/latest_version?id={video_id}&itag=140",
            })

    except Exception as e:
        print(f"[ERROR /search] {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify(results), 200


@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Backend activo"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
