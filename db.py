import sqlite3
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            topic TEXT,
            is_random INTEGER DEFAULT 0,
            aspect TEXT NOT NULL,
            duration REAL DEFAULT 8,
            status TEXT DEFAULT 'pending',   -- pending / processing / done / error
            error_message TEXT,
            created_at REAL NOT NULL,
            started_at REAL,
            finished_at REAL,
            video_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            topic TEXT,
            text_content TEXT NOT NULL,
            aspect TEXT NOT NULL,
            filepath TEXT NOT NULL,
            thumb_path TEXT,
            palette TEXT,
            font TEXT,
            animation TEXT,
            text_animation TEXT,
            music_mood TEXT,
            duration REAL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            topic TEXT,
            text_content TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        """
    )
    conn.commit()
    # Crash recovery: any job left "processing" from a previous run that
    # was interrupted (app closed/crashed mid-render) goes back to pending
    # so it gets retried instead of hanging forever.
    conn.execute("UPDATE queue SET status='pending', started_at=NULL WHERE status='processing'")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def enqueue_job(category, topic, is_random, aspect, duration=8):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO queue (category, topic, is_random, aspect, duration, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (category, topic, int(is_random), aspect, duration, time.time()),
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return job_id


def get_next_pending_job():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_job_processing(job_id):
    conn = get_conn()
    conn.execute("UPDATE queue SET status='processing', started_at=? WHERE id=?", (time.time(), job_id))
    conn.commit()
    conn.close()


def mark_job_done(job_id, video_id):
    conn = get_conn()
    conn.execute(
        "UPDATE queue SET status='done', finished_at=?, video_id=? WHERE id=?",
        (time.time(), video_id, job_id),
    )
    conn.commit()
    conn.close()


def mark_job_error(job_id, message):
    conn = get_conn()
    conn.execute(
        "UPDATE queue SET status='error', finished_at=?, error_message=? WHERE id=?",
        (time.time(), message, job_id),
    )
    conn.commit()
    conn.close()


def get_queue(limit=100):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM queue ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def queue_counts():
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as c FROM queue GROUP BY status"
    ).fetchall()
    conn.close()
    return {r["status"]: r["c"] for r in rows}


# ---------------------------------------------------------------------------
# Videos
# ---------------------------------------------------------------------------

def save_video(category, topic, text_content, aspect, filepath, thumb_path,
               palette, font, animation, text_animation, music_mood, duration):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO videos
           (category, topic, text_content, aspect, filepath, thumb_path, palette,
            font, animation, text_animation, music_mood, duration, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (category, topic, text_content, aspect, filepath, thumb_path, palette,
         font, animation, text_animation, music_mood, duration, time.time()),
    )
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return vid


def get_videos(limit=200, category=None):
    conn = get_conn()
    if category and category != "all":
        rows = conn.execute(
            "SELECT * FROM videos WHERE category=? ORDER BY created_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_video(video_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_video(video_id):
    conn = get_conn()
    conn.execute("DELETE FROM videos WHERE id=?", (video_id,))
    conn.commit()
    conn.close()


def video_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
    by_cat = conn.execute(
        "SELECT category, COUNT(*) c FROM videos GROUP BY category"
    ).fetchall()
    conn.close()
    return {"total": total, "by_category": {r["category"]: r["c"] for r in by_cat}}


# ---------------------------------------------------------------------------
# Content history (record of generated text, to reduce repeats)
# ---------------------------------------------------------------------------

def save_content_history(category, topic, text_content):
    conn = get_conn()
    conn.execute(
        "INSERT INTO content_history (category, topic, text_content, created_at) VALUES (?,?,?,?)",
        (category, topic, text_content, time.time()),
    )
    conn.commit()
    conn.close()


def recent_texts(category, limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT text_content FROM content_history WHERE category=? ORDER BY created_at DESC LIMIT ?",
        (category, limit),
    ).fetchall()
    conn.close()
    return {r["text_content"] for r in rows}
