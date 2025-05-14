from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import instaloader
import requests
import os
import datetime
import random
import time
from fake_useragent import UserAgent

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

loader = instaloader.Instaloader()
ua = UserAgent()

HEADERS_LIST = [
    {"User-Agent": ua.random, "Accept-Language": "en-US,en;q=0.9"},
    {"User-Agent": ua.random, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9"},
    {"User-Agent": ua.random, "Referer": "https://www.google.com/"},
]

def get_random_headers():
    return random.choice(HEADERS_LIST)

def generate_filename(extension):
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"Downsnap-{timestamp}.{extension}"

def get_shortcode(url_or_shortcode):
    """Extracts shortcode from full URL or returns as-is"""
    if '/' in url_or_shortcode:
        return url_or_shortcode.strip('/').split("/")[-1]
    return url_or_shortcode

@app.route("/preview", methods=["GET"])
def preview():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    shortcode = get_shortcode(url)

    try:
        time.sleep(random.uniform(1.5, 3.0))
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        media_items = []

        if post.typename == "GraphSidecar":
            for idx, node in enumerate(post.get_sidecar_nodes()):
                media_items.append({
                    "index": idx,
                    "type": "video" if node.is_video else "image",
                    "url": node.video_url if node.is_video else node.display_url
                })
        else:
            media_items.append({
                "index": 0,
                "type": "video" if post.is_video else "image",
                "url": post.video_url if post.is_video else post.url
            })

        return jsonify({
            "username": post.owner_username,
            "caption": post.caption or "",
            "media_items": media_items
        })

    except Exception as e:
        return jsonify({"error": f"Failed to fetch post: {str(e)}"}), 400

@app.route("/profile-pic", methods=["GET"])
def profile_pic():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        return jsonify({
            "username": profile.username,
            "media_items": [{
                "type": "image",
                "url": profile.profile_pic_url_hd
            }]
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch profile: {str(e)}"}), 400

@app.route("/stories", methods=["GET"])
def stories():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        loader.load_session_from_file()  # You must log in and save session first
        stories = loader.get_stories(userids=[profile.userid])

        story_items = []
        for story in stories:
            for item in story.get_items():
                story_items.append({
                    "type": "video" if item.is_video else "image",
                    "url": item.video_url if item.is_video else item.url
                })

        if not story_items:
            return jsonify({"message": "No active stories found."})

        return jsonify({
            "username": profile.username,
            "media_items": story_items
        })

    except Exception as e:
        return jsonify({"error": f"Failed to fetch stories: {str(e)}"}), 400

@app.route("/download", methods=["GET"])
def download():
    media_url = request.args.get("media_url")
    if not media_url:
        return jsonify({"error": "media_url is required"}), 400

    try:
        ext = "mp4" if ".mp4" in media_url or "video" in media_url else "jpg"
        filename = generate_filename(ext)
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        response = requests.get(media_url, headers=get_random_headers(), stream=True)

        if response.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({"error": f"Download failed with status {response.status_code}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
