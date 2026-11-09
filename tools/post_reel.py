#!/usr/bin/env python3
"""Turn PFG Reel masters (square, trimmed clips) into a finished 9:16 post.

Single clip:  post_reel.py OUT --clip master.mp4 --hook1 .. --hook2 .. --cues "A|B|C" --name ".." --theme power
Montage:      post_reel.py OUT --clip a.mp4 --clip b.mp4 --clip c.mp4 --labels "1. A|2. B|3. C" --seg 5 ...
Every post ends on a 2.2 s PFG logo end card with one call to action.
"""
import argparse, json, subprocess
from pathlib import Path

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
LOGO = HERE / "pfg_logo.png"
W, H, FPS, BOX, BOX_Y, END = 1080, 1920, 30, 960, 640, 2.2
THEMES = {"rotation": "0x3FBF63", "power": "0xFF8A1F", "mobility": "0x2EC4D6", "back": "0xF2C230"}
GREEN = "0x3FBF63"
XB, B, SB = (FONTS / f for f in ("BarlowCondensed-ExtraBold.ttf", "BarlowCondensed-Bold.ttf", "Barlow-SemiBold.ttf"))


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%").replace(",", "\\,")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout)


def build(out, clips, hook1, hook2, cues, name, theme, cta, labels=None, seg=5.0, badge="DOCTOR OF PHYSICAL THERAPY  •  TPI CERTIFIED"):
    acc = THEMES[theme]
    inputs, parts, total = [], [], 0.0
    montage = len(clips) > 1
    for i, c in enumerate(clips):
        d = dur(c)
        if montage:  # take a centred window of each clip
            take = min(seg, d)
            ss = max((d - take) / 2, 0)
            inputs += ["-ss", f"{ss:.2f}", "-t", f"{take:.2f}", "-i", c]
            d = take
        else:
            inputs += ["-i", c]
        parts.append((i, total, total + d))
        total += d
    n = len(clips)
    fc = ""
    for i, t0, t1 in parts:
        fc += f"[{i}:v]fps={FPS},scale={BOX}:{BOX},setsar=1,setpts=PTS-STARTPTS[c{i}];"
    fc += "".join(f"[c{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[clip];"
    fc += "[clip]split[a][b];"
    fc += (f"[a]scale={H}:{H},crop={W}:{H},boxblur=30:3,eq=brightness=-0.35:saturation=0.5[bg];")
    zoom_at = total * 0.45
    if montage:
        fc += "[b]null[fg];"
    else:
        fc += (f"[b]zoompan=z='if(gte(in_time,{zoom_at:.2f}),min(zoom+0.004,1.10),1)':"
               f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={BOX}x{BOX}:fps={FPS}[fg];")
    draw = [
        f"drawbox=x={(W-BOX)//2}:y={BOX_Y + BOX}:w={BOX}:h=10:color={acc}:t=fill",
        f"drawtext=fontfile='{B}':text='PHYSIO FORE GOLF':fontsize=34:fontcolor=white@0.9:x=(w-text_w)/2:y=190",
        f"drawtext=fontfile='{SB}':text='{esc(badge)}':fontsize=26:fontcolor={acc}:x=(w-text_w)/2:y=232",
        f"drawtext=fontfile='{XB}':text='{esc(hook1)}':fontsize=108:fontcolor=white:x=(w-text_w)/2:y=290",
        f"drawtext=fontfile='{XB}':text='{esc(hook2)}':fontsize=108:fontcolor=black:box=1:boxcolor={acc}:"
        f"boxborderw=16:x=(w-text_w)/2:y=418",
    ]
    if montage:
        for (i, t0, t1), lab in zip(parts, labels.split("|")):
            draw.append(f"drawtext=fontfile='{XB}':text='{esc(lab.upper())}':fontsize=54:fontcolor=black:box=1:"
                        f"boxcolor={acc}:boxborderw=14:x=(w-text_w)/2:y={BOX_Y - 72}:enable='between(t,{t0:.2f},{t1:.2f})'")
        if cues:
            draw.append(f"drawtext=fontfile='{XB}':text='{esc(cues.upper())}':fontsize=54:fontcolor=white:box=1:"
                        f"boxcolor=black@0.55:boxborderw=16:x=(w-text_w)/2:y={BOX_Y + BOX - 110}")
    else:
        draw.append(f"drawtext=fontfile='{B}':text='{esc(name.upper())}':fontsize=40:fontcolor=white@0.85:"
                    f"x=(w-text_w)/2:y={BOX_Y - 58}")
        cl = [c.strip() for c in cues.split("|") if c.strip()]
        span = (total - 1.0) / max(len(cl), 1)
        for i, c in enumerate(cl):
            t0, t1 = 1.0 + i * span, 1.0 + (i + 1) * span
            draw.append(f"drawtext=fontfile='{XB}':text='{esc(c.upper())}':fontsize=58:fontcolor=white:box=1:"
                        f"boxcolor=black@0.55:boxborderw=18:x=(w-text_w)/2:y={BOX_Y + BOX - 120}:"
                        f"alpha='if(lt(t,{t0}+0.25),(t-{t0})/0.25,1)':enable='between(t,{t0:.2f},{t1:.2f})'")
    fc += f"[bg][fg]overlay=(W-w)/2:{BOX_Y}," + ",".join(draw) + ",format=yuv420p,setsar=1[main];"
    li = n
    fc += (f"color=c=black:s={W}x{H}:r={FPS}:d={END}[ec0];[{li}:v]scale=900:-1,format=rgba[lg];"
           f"[ec0][lg]overlay=(W-w)/2:620,"
           f"drawtext=fontfile='{B}':text='PLAY PAIN-FREE  •  MOVE BETTER  •  SWING LONGER':fontsize=34:"
           f"fontcolor=white@0.8:x=(w-text_w)/2:y=1110,"
           f"drawbox=x=150:y=1200:w=780:h=110:color={GREEN}:t=fill,"
           f"drawtext=fontfile='{XB}':text='{esc(cta)}':fontsize=50:fontcolor=black:x=(w-text_w)/2:y=1228,"
           f"drawtext=fontfile='{SB}':text='physioforegolf.com':fontsize=38:fontcolor=white:x=(w-text_w)/2:y=1350,"
           f"fade=t=in:st=0:d=0.25,format=yuv420p,setsar=1[end];[main][end]concat=n=2:v=1:a=0[v]")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-loop", "1", "-t", str(END), "-i", str(LOGO),
           "-filter_complex", fc, "-map", "[v]", "-an", "-c:v", "libx264", "-profile:v", "high",
           "-preset", "veryfast", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    return round(total + END, 1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("out"); p.add_argument("--clip", action="append", required=True)
    p.add_argument("--hook1", required=True); p.add_argument("--hook2", required=True)
    p.add_argument("--cues", default=""); p.add_argument("--name", default="")
    p.add_argument("--labels"); p.add_argument("--seg", type=float, default=5.0)
    p.add_argument("--theme", default="rotation", choices=THEMES)
    p.add_argument("--cta", default="SAVE THIS FOR YOUR NEXT WORKOUT")
    p.add_argument("--badge", default="DOCTOR OF PHYSICAL THERAPY  •  TPI CERTIFIED")
    a = p.parse_args()
    print(build(a.out, a.clip, a.hook1, a.hook2, a.cues, a.name, a.theme, a.cta, a.labels, a.seg, a.badge))
