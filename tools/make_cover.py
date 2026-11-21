#!/usr/bin/env python3
"""Make a Reel cover (1080x1920 JPG) for the profile grid.

The grid crops Reels to the middle 3:4, so everything important sits between y=240 and y=1680.
Covers should NOT all look alike: pick a different --style from the last few posts.

  photo  full-bleed still from the clip, title low-centre over a dark fade
  split  still on top, solid dark panel with the title below
  type   no photo: big type on the dark brand background (good for myths / tests)

usage: make_cover.py OUT --title "LINE ONE|LINE TWO" [--hl 2] [--clip library/x.mp4 --at 0.5]
                     [--style photo|split|type] [--theme rotation|power|mobility|back] [--kicker "SELF-TEST"]
--at is a fraction of the clip length (0-1). --hl is the 1-based line shown on an accent highlight.
"""
import argparse, base64, subprocess, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
THEMES = {"rotation": "#3FBF63", "power": "#FF8A1F", "mobility": "#2EC4D6", "back": "#F2C230"}


def still(clip, at):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                             capture_output=True, text=True, check=True).stdout)
    out = Path(tempfile.mkdtemp()) / "s.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at * d:.2f}", "-i", clip, "-frames:v", "1", "-q:v", "2",
                    str(out)], check=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def html(title, hl, img, style, acc, kicker):
    lines = []
    for i, t in enumerate(title.split("|"), 1):
        lines.append(f"<span class='hl'>{t}</span>" if i == hl else t)
    t = "<br>".join(lines)
    f = lambda n: f"url('file://{FONTS}/{n}')"
    css = f"""
    @font-face{{font-family:XB;src:{f('BarlowCondensed-ExtraBold.ttf')}}}
    @font-face{{font-family:CB;src:{f('BarlowCondensed-Bold.ttf')}}}
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1920px;background:#111311;color:#fff;position:relative;overflow:hidden}}
    .img{{position:absolute;left:0;top:0;width:1080px;object-fit:cover}}
    h1{{font-family:XB;text-transform:uppercase;line-height:1.02;position:absolute;left:70px;right:70px}}
    .hl{{background:{acc};color:#000;padding:0 18px;box-decoration-break:clone;-webkit-box-decoration-break:clone}}
    .k{{font-family:CB;font-size:46px;letter-spacing:10px;color:{acc};position:absolute;left:74px}}
    .brand{{font-family:CB;font-size:36px;letter-spacing:5px;color:rgba(255,255,255,.7);position:absolute;left:74px;top:1600px}}
    """
    k = f"<div class='k' style='top:{{y}}px'>{kicker}</div>" if kicker else ""
    if style == "photo":
        body = (f"<img class='img' style='height:1920px' src='{img}'>"
                "<div style='position:absolute;inset:0;background:linear-gradient(rgba(0,0,0,0) 35%,rgba(0,0,0,.85) 72%)'></div>"
                + k.format(y=1050) + f"<h1 style='top:1120px;font-size:150px'>{t}</h1>")
    elif style == "split":
        body = (f"<img class='img' style='height:1060px' src='{img}'>"
                f"<div style='position:absolute;left:0;right:0;top:1060px;height:14px;background:{acc}'></div>"
                + k.format(y=1130) + f"<h1 style='top:1200px;font-size:140px'>{t}</h1>")
    else:  # type
        body = k.format(y=470) + f"<h1 style='top:560px;font-size:190px'>{t}</h1>"
    return f"<html><head><style>{css}</style></head><body>{body}<div class='brand'>PHYSIO FORE GOLF</div></body></html>"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("out"); p.add_argument("--title", required=True); p.add_argument("--hl", type=int, default=0)
    p.add_argument("--clip"); p.add_argument("--at", type=float, default=0.5)
    p.add_argument("--style", default="photo", choices=["photo", "split", "type"])
    p.add_argument("--theme", default="rotation", choices=THEMES); p.add_argument("--kicker", default="")
    a = p.parse_args()
    img = still(a.clip, a.at) if a.clip and a.style != "type" else ""
    doc = Path(tempfile.mkdtemp()) / "c.html"
    doc.write_text(html(a.title, a.hl, img, a.style, THEMES[a.theme], a.kicker))
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{doc}"); pg.wait_for_timeout(300)
        pg.screenshot(path=a.out, type="jpeg", quality=90); b.close()
    print(a.out)
