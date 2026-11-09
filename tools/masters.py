#!/usr/bin/env python3
"""Make a clean Reel master from each original clip: logo intro/outro trimmed,
black bars removed, a square crop that follows the athlete, 960x960 H.264, no audio.
Text, colours and the end card are added later, per post.

usage: masters.py OUT_DIR SRC [SRC ...]   (skips masters that already exist)
"""
import json, os, re, subprocess, sys, unicodedata
from pathlib import Path
from make_reel import probe, bars_crop, motion_center_x, logo_trim

SIZE = 960


def slug(name):
    n = unicodedata.normalize("NFKD", name).replace("□", "-").replace("/", "-")
    n = re.sub(r"\(\d\)|-copy", "", Path(n).stem)
    n = re.sub(r"[^A-Za-z0-9&+]+", "-", n).strip("-").lower()
    return n


def master(src, out_dir):
    out = Path(out_dir) / f"{slug(os.path.basename(src))}.mp4"
    if out.exists() and out.stat().st_size > 10000:
        return {"src": src, "out": out.name, "skipped": True}
    w, h, full = probe(src)
    ss, to = logo_trim(src, full)
    cw, ch, cx, cy = bars_crop(src, ss, to) or (w, h, 0, 0)
    side = min(cw, ch)
    centre = motion_center_x(src, (cw, ch, cx, cy), to - ss, ss, to)
    x0 = int(round(min(max(centre * cw - side / 2, 0), cw - side)))
    tmp = out.with_suffix(".part.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-to", f"{to:.3f}", "-i", src,
                    "-vf", f"crop={side}:{side}:{cx + x0}:{cy},scale={SIZE}:{SIZE},fps=30,format=yuv420p",
                    "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-maxrate", "4M",
                    "-bufsize", "8M", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.rename(out)
    return {"src": src, "out": out.name, "start": round(ss, 2), "end": round(to, 2),
            "dur": round(to - ss, 1), "centre": round(centre, 3)}


if __name__ == "__main__":
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    log = open(os.path.join(out_dir, "_log.jsonl"), "a")
    for src in sys.argv[2:]:
        try:
            r = master(src, out_dir)
        except Exception as e:  # keep going; report at the end
            r = {"src": src, "error": str(e)[:300]}
        log.write(json.dumps(r) + "\n"); log.flush()
        print(json.dumps(r), flush=True)
