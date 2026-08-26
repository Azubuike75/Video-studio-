"""
Background queue worker. Runs in a daemon thread inside the Flask process
(see app.py). Pulls pending jobs one at a time, generates text (if needed),
renders the video locally, and stores the result — fully offline.
"""
import random
import threading
import time
import traceback

import db
from generator.text_gen import generate_text
from generator.video_gen import generate_video

_stop_event = threading.Event()
_status_lock = threading.Lock()
_current_status = {"active": False, "job_id": None, "detail": ""}


def get_worker_status():
    with _status_lock:
        return dict(_current_status)


def _set_status(**kwargs):
    with _status_lock:
        _current_status.update(kwargs)


def process_one_job(job):
    job_id = job["id"]
    db.mark_job_processing(job_id)
    _set_status(active=True, job_id=job_id, detail="writing content")
    try:
        category = job["category"]
        topic = None if job["is_random"] else (job["topic"] or None)

        # Avoid repeating the last ~50 lines used for this category
        seen = db.recent_texts(category, limit=50)
        text, used_topic = generate_text(category, topic)
        attempts = 0
        while text in seen and attempts < 10:
            text, used_topic = generate_text(category, topic)
            attempts += 1

        db.save_content_history(category, used_topic, text)

        _set_status(detail="rendering video")
        video_job = {
            "category": category,
            "topic": used_topic,
            "text": text,
            "aspect": job["aspect"],
            "duration": job["duration"],
        }
        seed = random.randint(0, 10_000_000)
        result = generate_video(video_job, seed=seed)

        video_id = db.save_video(
            category=category,
            topic=used_topic,
            text_content=text,
            aspect=job["aspect"],
            filepath=result["filepath"],
            thumb_path=result["thumb_path"],
            palette=result["palette"],
            font=result["font"],
            animation=result["animation"],
            text_animation=result["text_animation"],
            music_mood=result["music_mood"],
            duration=job["duration"],
        )
        db.mark_job_done(job_id, video_id)
    except Exception as e:
        db.mark_job_error(job_id, f"{e}\n{traceback.format_exc()[-1500:]}")
    finally:
        _set_status(active=False, job_id=None, detail="")


def worker_loop(poll_interval=1.0):
    while not _stop_event.is_set():
        job = db.get_next_pending_job()
        if job:
            process_one_job(job)
        else:
            time.sleep(poll_interval)


_thread = None


def start_worker_thread():
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _thread = threading.Thread(target=worker_loop, daemon=True)
    _thread.start()


def stop_worker_thread():
    _stop_event.set()
