"""
Video generation engine.
Pure local pipeline: Pillow renders a high-res background+text still image,
FFmpeg animates it (Ken Burns zoom/pan or fade) and mixes in a synthesized
music track, producing an MP4. No AI models, no network calls, no paid APIs.
"""
import os
import random
import subprocess
import textwrap
import uuid

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .style_bank import (
    FONTS, PALETTES, ANIMATIONS, TEXT_ANIMATIONS, CATEGORY_MOOD_BIAS,
    ASPECT_RATIOS, font_path, music_file_for_mood,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "videos")
THUMB_DIR = os.path.join(BASE_DIR, "outputs", "thumbs")
RENDER_SCALE = 1.15  # render background slightly larger than target so Ken Burns has room to move


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _make_gradient(w, h, c1, c2, diagonal=True):
    img = Image.new("RGB", (w, h), c1)
    px = img.load()
    if diagonal:
        maxsum = w + h
        for y in range(h):
            for x in range(0, w, 4):  # step 4 for speed, then resize smooths it
                t = (x + y) / maxsum
                col = _lerp_color(c1, c2, t)
                for dx in range(4):
                    if x + dx < w:
                        px[x + dx, y] = col
    else:
        for y in range(h):
            t = y / h
            col = _lerp_color(c1, c2, t)
            for x in range(w):
                px[x, y] = col
    return img


def _add_texture(img, seed=0):
    """Subtle soft blobs/vignette for visual interest, fully procedural."""
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    for _ in range(6):
        r = rng.randint(int(w * 0.15), int(w * 0.35))
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rng.randint(15, 35))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=w * 0.05))
    black = Image.new("RGB", (w, h), (255, 255, 255))
    img = Image.composite(black, img, overlay)

    # vignette
    vign = Image.new("L", (w, h), 0)
    vdraw = ImageDraw.Draw(vign)
    vdraw.ellipse([-w * 0.25, -h * 0.25, w * 1.25, h * 1.25], fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(radius=w * 0.08))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    img = Image.composite(img, dark, vign)
    return img


def _wrap_text_to_fit(draw, text, font_file, max_width, max_font_size, min_font_size=28):
    size = max_font_size
    while size >= min_font_size:
        font = ImageFont.truetype(font_file, size)
        avg_char_w = font.getlength("n") or (size * 0.55)
        wrap_width = max(10, int(max_width / avg_char_w))
        lines = textwrap.wrap(text, width=wrap_width, break_long_words=False)
        total_h = 0
        max_line_w = 0
        line_heights = []
        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1] + int(size * 0.35)
            max_line_w = max(max_line_w, lw)
            line_heights.append(lh)
            total_h += lh
        if max_line_w <= max_width and len(lines) <= 8:
            return font, lines, total_h, line_heights
        size -= 4
    font = ImageFont.truetype(font_file, min_font_size)
    lines = textwrap.wrap(text, width=max(10, int(max_width / (min_font_size * 0.55))))
    line_heights = []
    total_h = 0
    for line in lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1] + int(min_font_size * 0.35)
        line_heights.append(lh)
        total_h += lh
    return font, lines, total_h, line_heights


def render_still(text, category, topic, palette, font_choice, out_w, out_h, seed=None):
    """Render the base background+text still image at RENDER_SCALE for Ken Burns room."""
    rng = random.Random(seed)
    rw, rh = int(out_w * RENDER_SCALE), int(out_h * RENDER_SCALE)

    img = _make_gradient(rw, rh, palette["bg1"], palette["bg2"], diagonal=True)
    img = _add_texture(img, seed=rng.randint(0, 99999))
    draw = ImageDraw.Draw(img)

    # Category label (small pill top area)
    label_font = ImageFont.truetype(font_path("Poppins-Medium.ttf"), int(rh * 0.028))
    label = category.upper()
    lb = label_font.getbbox(label)
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    pad_x, pad_y = int(rw * 0.03), int(rh * 0.012)
    pill_w, pill_h = lw + pad_x * 2, lh + pad_y * 2
    pill_x = (rw - pill_w) // 2
    pill_y = int(rh * 0.10)
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=pill_h // 2, fill=palette["accent"],
    )
    draw.text((pill_x + pad_x, pill_y + pad_y - lb[1]), label, font=label_font,
              fill=(20, 20, 20))

    # Main text, centered, wrapped to fit
    max_width = int(rw * 0.82)
    max_font = int(rh * 0.075)
    font, lines, total_h, line_heights = _wrap_text_to_fit(
        draw, text, font_path(font_choice["file"]), max_width, max_font
    )
    start_y = (rh - total_h) // 2
    y = start_y
    for line, lh in zip(lines, line_heights):
        bbox = font.getbbox(line)
        lwid = bbox[2] - bbox[0]
        x = (rw - lwid) // 2
        # soft shadow for legibility
        shadow_off = max(2, int(max_font * 0.03))
        draw.text((x + shadow_off, y + shadow_off), line, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font, fill=palette["text"])
        y += lh

    # topic tag near bottom
    tag_font = ImageFont.truetype(font_path("Poppins-Medium.ttf"), int(rh * 0.022))
    tag = f"#{topic.replace(' ', '')}" if topic else ""
    if tag:
        tb = tag_font.getbbox(tag)
        tw = tb[2] - tb[0]
        draw.text(((rw - tw) // 2, int(rh * 0.90)), tag, font=tag_font, fill=palette["accent"])

    return img


def _ffmpeg_animation_filter(animation, out_w, out_h, render_w, render_h, duration, fps):
    """Build the ffmpeg filter_complex string for the chosen animation."""
    total_frames = int(duration * fps)
    if animation in ("zoom_in", "zoom_out"):
        zoom_start, zoom_end = (1.0, 1.12) if animation == "zoom_in" else (1.12, 1.0)
        # zoompan needs a static image input treated as a "video" of 1 frame
        return (
            f"scale={render_w}:{render_h},"
            f"zoompan=z='{zoom_start}+({zoom_end}-{zoom_start})*on/{total_frames}':"
            f"d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={out_w}x{out_h}:fps={fps}"
        )
    elif animation in ("pan_left", "pan_right"):
        max_x = render_w - out_w
        max_y = render_h - out_h
        if animation == "pan_left":
            xexpr = f"'(t/{duration})*{max_x}'"
        else:
            xexpr = f"'{max_x}-(t/{duration})*{max_x}'"
        return (
            f"scale={render_w}:{render_h},"
            f"crop={out_w}:{out_h}:x={xexpr}:y={max_y // 2},fps={fps}"
        )
    elif animation == "fade_pulse":
        return (
            f"scale={render_w}:{render_h},crop={out_w}:{out_h},"
            f"eq=brightness='0.03*sin(2*PI*t/3)':fps={fps}"
        )
    else:  # static_fade
        return f"scale={render_w}:{render_h},crop={out_w}:{out_h},fps={fps}"


def generate_video(job, seed=None):
    """
    job: dict with keys: category, topic, text, aspect (vertical/square/horizontal),
         duration (seconds, default 8)
    Returns dict with filepath, thumb_path, and the style choices used.
    """
    rng = random.Random(seed)
    category = job["category"]
    topic = job.get("topic") or ""
    text = job["text"]
    aspect = job.get("aspect", "vertical")
    duration = float(job.get("duration", 8))
    out_w, out_h = ASPECT_RATIOS[aspect]

    palette = rng.choice(PALETTES)
    font_choice = rng.choice(FONTS)
    animation = rng.choice(ANIMATIONS)
    text_anim = rng.choice(TEXT_ANIMATIONS)
    mood = rng.choice(CATEGORY_MOOD_BIAS.get(category, ["ambient"]))
    music_path = music_file_for_mood(mood)

    render_w, render_h = int(out_w * RENDER_SCALE), int(out_h * RENDER_SCALE)
    still = render_still(text, category, topic, palette, font_choice, out_w, out_h, seed=seed)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(THUMB_DIR, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    still_path = os.path.join(OUTPUT_DIR, f"_tmp_{uid}.png")
    thumb_path = os.path.join(THUMB_DIR, f"{uid}.jpg")
    out_path = os.path.join(OUTPUT_DIR, f"{category}_{aspect}_{uid}.mp4")

    still.save(still_path)
    still.resize((out_w, out_h)).convert("RGB").save(thumb_path, "JPEG", quality=85)

    fps = 30
    vf = _ffmpeg_animation_filter(animation, out_w, out_h, render_w, render_h, duration, fps)
    # fade in/out for polish regardless of animation
    fade_dur = 0.5
    vf += f",fade=t=in:st=0:d={fade_dur},fade=t=out:st={max(0, duration - fade_dur)}:d={fade_dur}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", still_path,
        "-i", music_path,
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(still_path)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")

    return {
        "filepath": out_path,
        "thumb_path": thumb_path,
        "palette": palette["name"],
        "font": font_choice["name"],
        "animation": animation,
        "text_animation": text_anim,
        "music_mood": mood,
    }
