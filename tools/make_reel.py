#!/usr/bin/env python3
"""Turn a horizontal PFG exercise clip into a branded 9:16 Reel (H.264 MP4).

usage: make_reel.py SRC OUT --hook1 "LINE ONE" --hook2 "LINE TWO" --cues "CUE A • CUE B"
"""
import argparse, collections, json, re, subprocess, sys
from pathlib import Path
import numpy as np

FONTS = Path(__file__).parent / "fonts"
GREEN = "0x3FBF63"
W, H = 1080, 1920
BOX = 960           # foreground square size
BOX_Y = 590         # top of foreground square


def probe(src):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                                   "-show_streams", "-show_format", src],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return v["width"], v["height"], float(d["format"]["duration"])


def bars_crop(src, ss=0, to=None):
    """Find the real picture inside any black pillar/letterbox bars."""
    win = ["-ss", str(ss)] + (["-to", str(to)] if to else [])
    out = subprocess.run(["ffmpeg", "-v", "info", *win, "-i", src, "-vf", "cropdetect=24:2:0",
                          "-t", "8", "-f", "null", "-"], capture_output=True, text=True).stderr
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", out)
    if not crops:
        return None
    # the largest frequent crop = the real picture (smaller ones are dark frames)
    counts = collections.Counter(crops)
    best = max(counts, key=lambda c: (counts[c] > len(crops) * 0.2, int(c[0]) * int(c[1])))
    return tuple(int(x) for x in best)


def motion_center_x(src, crop, dur, ss=0, to=None):
    """Horizontal centre of movement, so the square crop follows the athlete."""
    cw, ch, cx, cy = crop
    sw = 320
    sh = int(round(ch * sw / cw / 2) * 2)
    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={sw}:{sh},fps=4,format=gray"
    win = ["-ss", str(ss)] + (["-to", str(to)] if to else [])
    raw = subprocess.run(["ffmpeg", "-v", "error", *win, "-i", src, "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.int16)
    if len(frames) < 2:
        return 0.5
    diff = np.abs(np.diff(frames, axis=0)).sum(axis=0)          # sh x sw
    diff[diff < np.percentile(diff, 80)] = 0                   # keep strong motion only
    col = diff.sum(axis=0).astype(float)
    if col.sum() == 0:
        return 0.5
    return float((col * np.arange(sw)).sum() / col.sum() / sw)


def logo_trim(src, dur):
    """Skip the baked-in PFG logo intro/outro: they sit between black frames near each end."""
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-vf", "blackdetect=d=0.05:pix_th=0.10",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    gaps = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out)]
    start = max([b for a, b in gaps if b < 3.0], default=0.0)
    end = min([a for a, b in gaps if a > dur - 3.5 and a > start + 3], default=dur)
    return start, end


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def build(src, out, hook1, hook2, cues):
    w, h, dur = probe(src)
    crop = bars_crop(src) or (w, h, 0, 0)
    cw, ch, cx, cy = crop
    side = min(cw, ch)
    centre = motion_center_x(src, crop, dur)
    x0 = int(round(min(max(centre * cw - side / 2, 0), cw - side)))
    sq = f"crop={side}:{side}:{cx + x0}:{cy}"

    f_xb = FONTS / "BarlowCondensed-ExtraBold.ttf"
    f_b = FONTS / "BarlowCondensed-Bold.ttf"
    hook_size = 104
    fc = (
        f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=30:3,eq=brightness=-0.32:saturation=0.6[bg];"
        f"[0:v]{sq},scale={BOX}:{BOX}[fg];"
        f"[bg][fg]overlay=(W-w)/2:{BOX_Y},"
        f"drawbox=x={(W-BOX)//2}:y={BOX_Y + BOX}:w={BOX}:h=8:color={GREEN}:t=fill,"
        f"drawtext=fontfile='{f_b}':text='PHYSIO FORE GOLF':fontsize=34:fontcolor=white@0.85:"
        f"x=(w-text_w)/2:y=215,"
        f"drawtext=fontfile='{f_xb}':text='{esc(hook1)}':fontsize={hook_size}:fontcolor=white:"
        f"x=(w-text_w)/2:y=275,"
        f"drawtext=fontfile='{f_xb}':text='{esc(hook2)}':fontsize={hook_size}:fontcolor=black:"
        f"box=1:boxcolor={GREEN}:boxborderw=14:x=(w-text_w)/2:y=395,"
        f"drawtext=fontfile='{f_b}':text='{esc(cues)}':fontsize=44:fontcolor={GREEN}:"
        f"x=(w-text_w)/2:y=530,"
        f"format=yuv420p[v]"
    )
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]",
           "-an", "-r", "30", "-c:v", "libx264", "-profile:v", "high", "-preset", "veryfast",
           "-crf", "21", "-maxrate", "8M", "-bufsize", "16M", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    return {"crop": crop, "motion_centre": round(centre, 3), "square_x": cx + x0, "duration": round(dur, 1)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("src"); p.add_argument("out")
    p.add_argument("--hook1", required=True); p.add_argument("--hook2", required=True)
    p.add_argument("--cues", required=True)
    a = p.parse_args()
    print(json.dumps(build(a.src, a.out, a.hook1, a.hook2, a.cues)))
