# Video Studio — Private Offline Social Video Generator

A private, single-admin web app that generates short social media videos
(Quotes, Facts, Tips, Stories, Jokes, Riddles) in vertical (9:16), square
(1:1), and horizontal (16:9) formats — automatically, in bulk, and
**entirely offline**. No AI models, no paid APIs, no internet connection
required after installation.

How it works, in short:
- **Text** comes from a local content engine (curated lines + template
  combinatorics) — effectively unlimited variety, all generated on your
  machine.
- **Backgrounds, fonts, colors, and animations** are randomly combined from
  a local style bank and rendered with Pillow + FFmpeg.
- **Music** is a handful of short royalty-free tracks synthesized locally
  (not downloaded), so there's no licensing concern.
- Everything is stored in a local SQLite database and an `outputs/` folder
  on your own disk.

---

## 1. Prerequisites

- **Python 3.10+**
- **FFmpeg** installed and available on your PATH
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from https://ffmpeg.org/download.html and add the
    `bin` folder to your PATH

## 2. Install & Run

**macOS / Linux**
```bash
cd socialvid
chmod +x run.sh
./run.sh
```

**Windows**
```
cd socialvid
run.bat
```

Either script creates a local virtual environment, installs the Python
dependencies (Flask, Pillow, numpy — all pinned in `requirements.txt`),
generates the local music tracks on first run, and starts the app.

Then open **http://127.0.0.1:5000** in your browser.

The first time you open it, you'll be asked to create your admin username
and password — this is the only account, and it never leaves your machine.

### Manual install (alternative)
```bash
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python3 app.py
```

## 3. Using the app

1. **Log in** with the admin account you created.
2. On the dashboard:
   - Pick a **category** (Quotes, Facts, Tips, Stories, Jokes, Riddles).
   - Type a **topic** (e.g. "coffee", "discipline", "chess") or leave it
     blank / hit **Random** for a random topic.
   - Choose one or more **formats** (Vertical / Square / Horizontal).
   - Set **quantity** (how many videos to generate) and **duration** in
     seconds (4–20s).
   - Click **Add to queue**.
3. The **Queue** panel shows live progress (pending → processing → done).
   Videos are generated one at a time in the background, so you can keep
   queuing more while earlier ones render — there's no hard limit on how
   many you queue.
4. Finished videos appear in the **Saved videos** gallery. Click a video to
   preview it, download the MP4, or delete it. Use the category dropdown to
   filter the gallery.
5. All generated videos remain saved in `outputs/videos/` (and are tracked
   in `data/app.db`) until you delete them from the app.

## 4. Where things live

```
socialvid/
  app.py                 Flask app (routes, login, queue API)
  db.py                  SQLite schema + queries
  auth.py                Single-admin auth
  worker.py               Background queue processor
  generator/
    text_gen.py           Offline content engine (banks + templates)
    style_bank.py          Palettes, fonts, animation & music presets
    video_gen.py            Pillow + FFmpeg video rendering
    make_music.py          One-time local music synthesis (numpy)
  assets/
    fonts/                Open-license fonts bundled with the app
    music/                Synthesized royalty-free tracks (.mp3)
  data/
    app.db                 SQLite database (queue, videos, auth)
  outputs/
    videos/                 Generated MP4s
    thumbs/                  Thumbnails for the gallery
  templates/, static/       Web UI (HTML/CSS/JS, no CDN dependencies)
```

## 5. Notes & tips

- **Speed**: each video typically renders in a few seconds to ~15 seconds
  depending on your machine and chosen duration — no GPU or AI inference
  involved.
- **Unlimited generation**: queue as many as you like; they process
  sequentially so your machine isn't overloaded. Leave the app running and
  come back later for a full batch.
- **Repetition control**: the app remembers recently generated lines per
  category and tries to avoid immediate repeats.
- **Customizing content**: open `generator/text_gen.py` to add your own
  quotes/facts/jokes/etc. to the banks, or add new templates — no code
  framework knowledge beyond basic Python is needed.
- **Customizing visuals**: `generator/style_bank.py` holds the color
  palettes, font list, and animation presets — add your own palette or
  swap in your own font files under `assets/fonts/`.
- **This app is for local/private use** by one admin. The built-in server
  is fine for personal use on your own machine or home network; it is not
  hardened for public internet deployment.
- **Resetting the admin account**: delete `data/auth.json` and restart the
  app to go through first-run setup again.
