"""
Generates short, loopable, royalty-free background music tracks entirely
offline using simple additive synthesis (numpy) -> WAV -> MP3 (ffmpeg).
Since the audio is synthesized locally by this script, there is no
licensing/copyright concern and no internet connection is required.

Run once at install time: python3 generator/make_music.py
"""
import os
import wave
import struct
import subprocess
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "music")
SR = 44100

# note frequencies (Hz), simple equal temperament from A4=440
NOTE_FREQ = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99,
}

CHORDS = {
    "Cmaj": ["C3", "E3", "G3", "C4"],
    "Am": ["A3", "C4", "E4"],
    "Fmaj": ["F3", "A3", "C4"],
    "Gmaj": ["G3", "B3", "D3"],
    "Dm": ["D3", "F3", "A3"],
    "Em": ["E3", "G3", "B3"],
}


def envelope(n, attack=0.05, release=0.3):
    env = np.ones(n)
    a = int(n * attack)
    r = int(n * release)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return env


def tone(freq, duration, sr=SR, harmonics=(1.0, 0.5, 0.25), vibrato=0.0):
    t = np.linspace(0, duration, int(sr * duration), False)
    wave_sig = np.zeros_like(t)
    for i, amp in enumerate(harmonics, start=1):
        f = freq * i
        if vibrato:
            f = f + vibrato * np.sin(2 * np.pi * 5 * t)
        wave_sig += amp * np.sin(2 * np.pi * f * t)
    wave_sig /= sum(harmonics)
    return wave_sig


def chord_pad(chord_notes, duration, sr=SR):
    sig = np.zeros(int(sr * duration))
    for note in chord_notes:
        freq = NOTE_FREQ[note]
        sig += tone(freq, duration, sr, harmonics=(1.0, 0.3, 0.15))
    sig /= len(chord_notes)
    sig *= envelope(len(sig), attack=0.15, release=0.5)
    return sig


def soft_kick(duration, sr=SR):
    t = np.linspace(0, duration, int(sr * duration), False)
    freq_sweep = 120 * np.exp(-8 * t)
    sig = np.sin(2 * np.pi * freq_sweep * t)
    sig *= np.exp(-10 * t)
    return sig


def build_track(mood, total_seconds=24, sr=SR):
    progressions = {
        "uplifting": ["Cmaj", "Gmaj", "Am", "Fmaj"],
        "chill": ["Am", "Fmaj", "Cmaj", "Gmaj"],
        "dramatic": ["Dm", "Am", "Fmaj", "Gmaj"],
        "playful": ["Cmaj", "Fmaj", "Gmaj", "Cmaj"],
        "ambient": ["Am", "Em", "Fmaj", "Cmaj"],
    }
    prog = progressions.get(mood, progressions["ambient"])
    bar_len = total_seconds / (len(prog) * 2)  # repeat progression twice
    full = np.zeros(int(sr * total_seconds) + sr)

    pos = 0.0
    beat_add_pulse = mood in ("uplifting", "playful")
    for rep in range(2):
        for chord_name in prog:
            pad = chord_pad(CHORDS[chord_name], bar_len, sr)
            start = int(pos * sr)
            end = start + len(pad)
            if end > len(full):
                pad = pad[: len(full) - start]
                end = len(full)
            full[start:end] += pad * 0.5

            if beat_add_pulse:
                kick = soft_kick(0.25, sr) * 0.25
                for beat in range(int(bar_len // 0.6)):
                    bstart = start + int(beat * 0.6 * sr)
                    bend = bstart + len(kick)
                    if bend < len(full):
                        full[bstart:bend] += kick

            pos += bar_len

    full = full[: int(sr * total_seconds)]
    # gentle overall fade in/out for seamless feel + normalize
    full *= envelope(len(full), attack=0.03, release=0.08)
    peak = np.max(np.abs(full)) or 1.0
    full = (full / peak) * 0.7
    return full


def write_wav(path, samples, sr=SR):
    samples_i16 = np.int16(np.clip(samples, -1, 1) * 32767)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack("<%dh" % len(samples_i16), *samples_i16))


def main():
    os.makedirs(MUSIC_DIR, exist_ok=True)
    moods = ["uplifting", "chill", "dramatic", "playful", "ambient"]
    for mood in moods:
        wav_path = os.path.join(MUSIC_DIR, f"{mood}.wav")
        mp3_path = os.path.join(MUSIC_DIR, f"{mood}.mp3")
        samples = build_track(mood, total_seconds=24)
        write_wav(wav_path, samples)
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "4", mp3_path],
            check=True, capture_output=True,
        )
        os.remove(wav_path)
        print(f"generated {mp3_path}")


if __name__ == "__main__":
    main()
