import os
import shutil
import sys
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    jsonify, send_file, abort, flash,
)

import db
import auth
import worker
from generator.style_bank import ASPECT_RATIOS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
db.init_db()
app.secret_key = auth.get_or_create_secret_key()

CATEGORIES = ["quotes", "facts", "tips", "stories", "jokes", "riddles"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth / setup
# ---------------------------------------------------------------------------

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if auth.is_configured():
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            auth.set_credentials(username, password)
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
    return render_template("setup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if not auth.is_configured():
        return redirect(url_for("setup"))
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if auth.verify(username, password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        categories=CATEGORIES,
        aspects=list(ASPECT_RATIOS.keys()),
        username=session.get("username"),
    )


# ---------------------------------------------------------------------------
# Queue actions
# ---------------------------------------------------------------------------

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    data = request.get_json(force=True)
    category = data.get("category", "quotes")
    if category not in CATEGORIES:
        return jsonify({"error": "invalid category"}), 400

    topic = (data.get("topic") or "").strip()
    is_random = bool(data.get("is_random")) or not topic
    aspects = data.get("aspects") or ["vertical"]
    aspects = [a for a in aspects if a in ASPECT_RATIOS] or ["vertical"]
    quantity = max(1, min(int(data.get("quantity", 1)), 200))
    duration = float(data.get("duration", 8))
    duration = min(max(duration, 4), 20)

    job_ids = []
    for _ in range(quantity):
        for aspect in aspects:
            job_ids.append(db.enqueue_job(category, topic, is_random, aspect, duration))

    worker.start_worker_thread()
    return jsonify({"ok": True, "queued": len(job_ids)})


@app.route("/api/queue")
@login_required
def api_queue():
    return jsonify({
        "jobs": db.get_queue(limit=100),
        "counts": db.queue_counts(),
        "worker": worker.get_worker_status(),
    })


@app.route("/api/videos")
@login_required
def api_videos():
    category = request.args.get("category", "all")
    videos = db.get_videos(limit=300, category=category)
    return jsonify({"videos": videos, "stats": db.video_stats()})


@app.route("/delete/<int:video_id>", methods=["POST"])
@login_required
def delete_video(video_id):
    video = db.get_video(video_id)
    if video:
        for path in (video["filepath"], video["thumb_path"]):
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        db.delete_video(video_id)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Media serving
# ---------------------------------------------------------------------------

@app.route("/media/video/<int:video_id>")
@login_required
def media_video(video_id):
    video = db.get_video(video_id)
    if not video or not os.path.exists(video["filepath"]):
        abort(404)
    return send_file(video["filepath"], mimetype="video/mp4")


@app.route("/media/thumb/<int:video_id>")
@login_required
def media_thumb(video_id):
    video = db.get_video(video_id)
    if not video or not video["thumb_path"] or not os.path.exists(video["thumb_path"]):
        abort(404)
    return send_file(video["thumb_path"], mimetype="image/jpeg")


@app.route("/download/<int:video_id>")
@login_required
def download_video(video_id):
    video = db.get_video(video_id)
    if not video or not os.path.exists(video["filepath"]):
        abort(404)
    filename = f"{video['category']}_{video['aspect']}_{video_id}.mp4"
    return send_file(video["filepath"], as_attachment=True, download_name=filename)


def _startup_checks():
    if shutil.which("ffmpeg") is None:
        print(
            "\nERROR: ffmpeg was not found on your PATH.\n"
            "This app needs ffmpeg installed locally to render videos.\n"
            "  - macOS:   brew install ffmpeg\n"
            "  - Ubuntu:  sudo apt install ffmpeg\n"
            "  - Windows: https://ffmpeg.org/download.html (add to PATH)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    music_dir = os.path.join(BASE_DIR, "assets", "music")
    needed = ["uplifting.mp3", "chill.mp3", "dramatic.mp3", "playful.mp3", "ambient.mp3"]
    if not all(os.path.exists(os.path.join(music_dir, f)) for f in needed):
        print("First run: generating local royalty-free music tracks...")
        from generator.make_music import main as make_music_main
        make_music_main()


if __name__ == "__main__":
    _startup_checks()
    worker.start_worker_thread()
    port = int(os.environ.get("PORT", 5000))
    print(f"\nVideo Studio running at http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
