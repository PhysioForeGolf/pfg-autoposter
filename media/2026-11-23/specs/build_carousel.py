#!/usr/bin/env python3
"""Week of 2026-11-23: Sunday carousel (1080x1350 JPGs) rendered from HTML with Playwright. Run from repo root."""
import base64, subprocess, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
FONTS = ROOT / "tools/fonts"
OUT = ROOT / "media/2026-11-23"
ACC = "#3FBF63"


def still(clip, t, crop=None):
    out = Path(tempfile.mkdtemp()) / "s.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(ROOT / "library" / clip), "-frames:v", "1",
                    "-q:v", "2", str(out)], check=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


CSS = f"""
@font-face{{font-family:XB;src:url('file://{FONTS}/BarlowCondensed-ExtraBold.ttf')}}
@font-face{{font-family:CB;src:url('file://{FONTS}/BarlowCondensed-Bold.ttf')}}
@font-face{{font-family:SB;src:url('file://{FONTS}/Barlow-SemiBold.ttf')}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:#111311;color:#fff;position:relative;overflow:hidden}}
.ph{{position:absolute;left:0;top:0;width:1080px;object-fit:cover}}
.fade{{position:absolute;left:0;right:0}}
.k{{font-family:CB;font-size:34px;letter-spacing:8px;color:{ACC};text-transform:uppercase}}
h1{{font-family:XB;text-transform:uppercase;line-height:1.0}}
.hl{{background:{ACC};color:#000;padding:0 14px;box-decoration-break:clone;-webkit-box-decoration-break:clone}}
p{{font-family:SB;font-size:34px;line-height:1.4;color:rgba(255,255,255,.88)}}
b{{color:#fff}}
.foot{{position:absolute;left:64px;right:64px;bottom:48px;display:flex;justify-content:space-between;font-family:CB;
      font-size:28px;letter-spacing:4px;color:rgba(255,255,255,.6);text-transform:uppercase}}
.foot .r{{color:{ACC}}}
.num{{position:absolute;left:52px;top:40px;font-family:XB;font-size:200px;line-height:1;color:transparent;
      -webkit-text-stroke:4px {ACC};text-shadow:0 6px 30px rgba(0,0,0,.4)}}
.dose{{display:inline-block;font-family:XB;font-size:46px;background:#fff;color:#000;padding:4px 18px;text-transform:uppercase}}
"""

COVER = ("bw-lunge-wrotation.mp4", 5.0)
MOVES = [
    ("bw-lunge-wrotation.mp4", 9.2, "Lunge + Rotation", "6 each side",
     "Club across your chest. Lunge, then turn over the front hip. Chest tall, knee over toes."),
    ("bw-sl-bridge.mp4", 3.0, "Single-Leg Bridge", "8 each side",
     "Drive through the heel and hold 2 seconds at the top. Keep your hips level."),
    ("bw-side-plank-hold.mp4", 4.0, "Side Plank", "20-30 s each side",
     "Long line from ear to ankle. Don't let the hips sag. Helps you resist the slide and sway."),
    ("bw-dead-bugs.mp4", 6.0, "Dead Bug", "6 each side, slow",
     "Ribs down, low back stays quiet. Reach the opposite arm and leg, then switch."),
]


def page(body):
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"


def slides():
    n = len(MOVES) + 1
    img = still(*COVER)
    yield page(
        f"<img class='ph' style='height:1350px;object-position:10% 50%' src='{img}'>"
        "<div class='fade' style='top:0;bottom:0;background:linear-gradient(rgba(17,19,17,0) 25%,rgba(17,19,17,.92) 62%,#111311 80%)'></div>"
        "<div style='position:absolute;left:64px;right:64px;top:720px'>"
        "<div class='k'>Save this · Holiday weekend</div>"
        "<h1 style='font-size:128px;margin-top:14px'>12-minute<br><span class='hl'>golf workout</span></h1>"
        "<p style='margin-top:26px'>Just you and a golf club. <b>4 moves, 3 rounds,</b> rest 45-60 s between rounds. "
        "Do it at home, at the in-laws' or in a hotel room.</p></div>"
        f"<div class='foot'><span>Physio Fore Golf</span><span class='r'>Swipe →</span></div>")
    for i, (clip, t, name, dose, cue) in enumerate(MOVES, 1):
        img = still(clip, t)
        last = i == len(MOVES)
        extra = ("<div style='margin-top:30px;padding-top:24px;border-top:2px solid rgba(255,255,255,.15)'>"
                 "<h1 style='font-size:60px'>Save this for <span class='hl'>your next trip</span></h1>"
                 f"<p style='margin-top:12px;color:{ACC}'>physioforegolf.com</p></div>") if last else ""
        top = 660 if not last else 600
        yield page(
            f"<img class='ph' style='height:{top + 40}px' src='{img}'>"
            f"<div class='fade' style='top:{top - 160}px;height:200px;background:linear-gradient(rgba(17,19,17,0),#111311)'></div>"
            f"<div class='num'>0{i}</div>"
            f"<div style='position:absolute;left:64px;right:64px;top:{top}px'>"
            f"<h1 style='font-size:92px'>{name}</h1>"
            f"<div class='dose' style='margin-top:16px'>{dose}</div>"
            f"<p style='margin-top:22px'>{cue}</p>{extra}</div>"
            f"<div class='foot'><span>Holiday golf workout</span><span class='r'>{i + 1}/{n}</span></div>")


if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(slides(), 1):
            f = tmp / f"{i}.html"
            f.write_text(html)
            pg.goto(f"file://{f}")
            pg.wait_for_timeout(250)
            out = OUT / f"sun-holiday-workout-{i}.jpg"
            pg.screenshot(path=str(out), type="jpeg", quality=90)
            print(out)
        b.close()
