#!/usr/bin/env python3
"""Full-screen 9:16 Reels with animated HTML text (built for the Nov 2026 watch-time rules).

Frame 1 is the movement, full screen, with the hook already on it. No header, no title card.
Text, labels, counters and the optional short end card are HTML/CSS (Barlow fonts), rendered
frame-by-frame with Playwright as a transparent layer and laid over the footage with ffmpeg.

usage: overlay_reel.py SPEC.json
SPEC = {
  "out": "media/2026-11-23/mon-ankle-test.mp4",
  "theme": "mobility",                      # rotation | power | mobility | back (accent colour)
  "segments": [                             # footage, back to back
     {"clip": "library/x.mp4", "start": 1.2, "dur": 3.0, "speed": 1.0, "cx": 0.5, "zoom": 1920}
  ],                                        # zoom = size the square master is scaled to (1920 = fill)
  "end": {"dur": 1.2, "cta": "SAVE THIS"},  # optional logo end card (keep under 1.5 s)
  "html": "<div class='a hook' data-t0='0' data-t1='4'>...</div>",   # animated elements
  "css": "extra css"
}
Animated element attributes: data-t0, data-t1 (seconds), data-in = none|pop|up|left|fade|wipe|grow,
data-out = fade|none. 'grow' animates width 0->100% across t0..t1 (progress bars).
"""
import base64, json, subprocess, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONTS = HERE / "fonts"
W, H, FPS = 1080, 1920, 30
THEMES = {"rotation": "#3FBF63", "power": "#FF8A1F", "mobility": "#2EC4D6", "back": "#F2C230"}

BASE_CSS = """
@font-face{font-family:XB;src:url('file://%(f)s/BarlowCondensed-ExtraBold.ttf')}
@font-face{font-family:CB;src:url('file://%(f)s/BarlowCondensed-Bold.ttf')}
@font-face{font-family:SB;src:url('file://%(f)s/Barlow-SemiBold.ttf')}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:transparent;overflow:hidden;color:#fff}
:root{--acc:%(acc)s}
.a{position:absolute;opacity:0}
.xb{font-family:XB;text-transform:uppercase;line-height:1.0}
.cb{font-family:CB;text-transform:uppercase}
.sb{font-family:SB}
.hl{background:var(--acc);color:#000;padding:2px 18px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.wb{background:#fff;color:#000;padding:2px 18px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.shadow{text-shadow:0 4px 24px rgba(0,0,0,.65),0 2px 4px rgba(0,0,0,.6)}
.brand{left:0;right:0;bottom:120px;text-align:center;font-family:CB;font-size:32px;letter-spacing:6px;color:rgba(255,255,255,.8)}
.end{inset:0;background:#000}
.end img{position:absolute;left:140px;width:800px;top:560px}
.end .tag{position:absolute;left:0;right:0;top:1030px;text-align:center;font-family:CB;font-size:34px;letter-spacing:3px;color:rgba(255,255,255,.8)}
.end .cta{position:absolute;left:130px;right:130px;top:1120px;padding:26px 10px;text-align:center;background:var(--acc);color:#000;font-family:XB;font-size:56px;text-transform:uppercase}
.end .web{position:absolute;left:0;right:0;top:1290px;text-align:center;font-family:SB;font-size:40px;color:#fff}
"""

ANIM_JS = """
window.setT = (t) => {
  const ease = x => 1 - Math.pow(1 - x, 3);
  const back = x => { const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  for (const el of document.querySelectorAll('.a')) {
    const t0 = parseFloat(el.dataset.t0 || 0), t1 = parseFloat(el.dataset.t1 || 999);
    const kind = el.dataset.in || 'fade', out = el.dataset.out || 'fade';
    if (t < t0 || t >= t1) { el.style.opacity = 0; continue; }
    const pin = kind === 'none' ? 1 : Math.min(1, (t - t0) / 0.28);
    const pout = out === 'none' ? 1 : Math.min(1, (t1 - t) / 0.18);
    let tr = '', op = Math.min(ease(pin), pout);
    if (kind === 'pop') tr = `scale(${0.6 + 0.4 * back(pin)})`;
    if (kind === 'up') tr = `translateY(${(1 - ease(pin)) * 80}px)`;
    if (kind === 'left') tr = `translateX(${(1 - ease(pin)) * -140}px)`;
    if (kind === 'wipe') { el.style.clipPath = `inset(0 ${100 - ease(pin) * 100}% 0 0)`; op = pout; }
    if (kind === 'grow') { el.style.width = (100 * Math.min(1, (t - t0) / (t1 - t0))) + '%'; op = 1; }
    el.style.opacity = op; el.style.transform = tr;
  }
};
"""


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True, check=True).stdout)


def footage(spec, tmp):
    """Concatenate the segments into a silent 1080x1920 clip (+ black tail for the end card)."""
    inputs, fc, n = [], "", 0
    for i, s in enumerate(spec["segments"]):
        sp = s.get("speed", 1.0)
        z = int(s.get("zoom", 1920))
        cx = s.get("cx", 0.5)
        inputs += ["-ss", f"{s['start']:.2f}", "-t", f"{s['dur'] * sp:.2f}", "-i", str(ROOT / s["clip"])]
        x = int(max(0, min(z - min(z, W), cx * z - min(z, W) / 2)))
        chain = f"[{i}:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS},scale={z}:{z},setsar=1"
        if z >= H:
            fc += f"{chain},crop={W}:{H}:{x}:{(z - H) // 2}[v{i}];"
        else:  # square shown big and centred, blurred copy behind it
            fc += (f"{chain},split[f{i}][b{i}];[b{i}]scale={H}:{H},crop={W}:{H},boxblur=30:3,eq=brightness=-0.35:saturation=0.6[bb{i}];"
                   f"[f{i}]crop={min(z, W)}:{z}:{x}:0[ff{i}];[bb{i}][ff{i}]overlay=(W-w)/2:(H-h)/2[v{i}];")
        n += 1
    end = spec.get("end")
    if end:
        fc += f"color=c=black:s={W}x{H}:r={FPS}:d={end['dur']}[v{n}];"
        n += 1
    fc += "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,format=yuv420p[out]"
    out = tmp / "bg.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "16", str(out)], check=True)
    return out


def page(spec):
    acc = THEMES[spec.get("theme", "rotation")]
    css = BASE_CSS % {"f": FONTS, "acc": acc} + spec.get("css", "")
    body = spec["html"]
    if spec.get("topfade", True):  # keeps the hook readable over busy or bright backgrounds
        body = ("<div class='a' data-t0='0' data-in='none' data-out='none' style='left:0;right:0;top:0;height:900px;"
                "background:linear-gradient(rgba(0,0,0,.55),rgba(0,0,0,.25) 55%,rgba(0,0,0,0))'></div>") + body
    if spec.get("brand", True):
        body += "<div class='a brand' data-t0='0' data-in='none'>PHYSIO FORE GOLF</div>"
    end = spec.get("end")
    if end:
        logo = "data:image/png;base64," + base64.b64encode((HERE / "pfg_logo.png").read_bytes()).decode()
        t0 = spec["_main"]
        body += (f"<div class='a end' data-t0='{t0:.2f}' data-in='fade' data-out='none'><img src='{logo}'>"
                 f"<div class='tag'>PLAY PAIN-FREE • MOVE BETTER • SWING LONGER</div>"
                 f"<div class='cta'>{end['cta']}</div><div class='web'>physioforegolf.com</div></div>")
    # brand line hides under the end card automatically (end card is opaque and later in the DOM)
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}<script>{ANIM_JS}</script></body></html>"


def render(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    main = sum(s["dur"] for s in spec["segments"])
    spec["_main"] = main
    total = main + (spec["end"]["dur"] if spec.get("end") else 0)
    tmp = Path(tempfile.mkdtemp())
    bg = footage(spec, tmp)
    (tmp / "o.html").write_text(page(spec))
    frames = tmp / "f"
    frames.mkdir()
    nf = int(round(total * FPS))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(f"file://{tmp / 'o.html'}")
        pg.wait_for_timeout(300)
        for i in range(nf):
            pg.evaluate(f"setT({i / FPS:.4f})")
            pg.screenshot(path=str(frames / f"{i:05d}.png"), omit_background=True)
        b.close()
    out = ROOT / spec["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bg), "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
                    "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]", "-map", "[v]",
                    "-an", "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20", "-maxrate", "8M",
                    "-bufsize", "16M", "-r", str(FPS), "-movflags", "+faststart", str(out)], check=True)
    return {"out": str(out), "seconds": round(total, 2), "frames": nf}


if __name__ == "__main__":
    print(json.dumps(render(sys.argv[1])))
