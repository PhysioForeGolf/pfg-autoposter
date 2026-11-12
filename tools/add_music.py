#!/usr/bin/env python3
"""Lay a song from audio/music/ under a finished (silent) Reel.

- Starts the song where it first reaches full energy (skips quiet intros).
- Evens out loudness (-14 LUFS), quick fade in, 2 s fade out over the logo end card.
- Video is copied untouched.

usage: add_music.py VIDEO SONG OUT [--start SECONDS]
"""
import argparse, json, re, subprocess
from pathlib import Path

MUSIC = Path(__file__).resolve().parent.parent / "audio" / "music"


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)


def energy_start(song, limit=25.0):
    """First moment the song's short-term loudness gets within 2 dB of its overall level."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-t", str(limit + 5), "-i", str(song), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    pts = [(float(t), float(s)) for t, s in re.findall(r"t:\s*([\d.]+).*?S:\s*(-?[\d.]+)", log)]
    lead = re.search(r"silence_end:\s*([\d.]+)", subprocess.run(
        ["ffmpeg", "-hide_banner", "-t", "6", "-i", str(song), "-af", "silencedetect=n=-40dB:d=0.2", "-f", "null", "-"],
        capture_output=True, text=True).stderr)
    lead = float(lead.group(1)) if lead else 0.0  # skip any silence at the very top
    if not pts:
        return lead
    target = max(s for _, s in pts) - 2.0
    for t, s in pts:
        if s >= target:
            return max(min(t - 3.0, limit), lead)  # short-term is a 3 s window: back up to where it began
    return lead


def add(video, song, out, start=None):
    song = Path(song) if Path(song).exists() else MUSIC / f"{song}.mp3"
    vd = dur(video)
    ss = energy_start(song) if start is None else start
    if ss + vd > dur(song):
        ss = max(dur(song) - vd, 0)
    fo = max(vd - 2.0, 0)
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.15,afade=t=out:st={fo:.2f}:d=2.0"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-ss", f"{ss:.2f}", "-t", f"{vd:.2f}", "-i", str(song),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)
    return {"song": song.stem, "song_start": round(ss, 2), "length": round(vd, 1)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video"); p.add_argument("song"); p.add_argument("out")
    p.add_argument("--start", type=float)
    a = p.parse_args()
    print(json.dumps(add(a.video, a.song, a.out, a.start)))
