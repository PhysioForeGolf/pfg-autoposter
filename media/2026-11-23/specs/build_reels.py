#!/usr/bin/env python3
"""Week of 2026-11-23: Reel specs for tools/overlay_reel.py (run from repo root)."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WEEK = "2026-11-23"
SPECS = Path(__file__).resolve().parent

CSS = """
.hook{left:60px;right:60px;top:250px;text-align:center;font-size:104px}
.hook2{left:60px;right:60px;text-align:center;font-size:96px}
.kick{left:0;right:0;text-align:center;font-family:CB;font-size:44px;letter-spacing:8px;color:var(--acc)}
.pill{left:0;right:0;text-align:center}
.pill span{display:inline-block;font-family:XB;text-transform:uppercase;font-size:64px;padding:10px 26px;background:#fff;color:#000;line-height:1.05}
.pill.acc span{background:var(--acc)}
.pill.dark span{background:rgba(0,0,0,.72);color:#fff}
.count{left:60px;top:250px;font-family:XB;font-size:120px;color:#000;background:var(--acc);padding:0 22px;line-height:1.05}
.shade{inset:0;background:rgba(10,12,10,.62)}
.bar{left:0;top:0;height:12px;background:var(--acc)}
"""


def reel(name, theme, segments, html, end=None, extra_css=""):
    spec = {"out": f"media/{WEEK}/{name}-silent.mp4", "theme": theme, "segments": segments, "html": html,
            "css": CSS + extra_css}
    if end:
        spec["end"] = end
    p = SPECS / f"{name}.json"
    p.write_text(json.dumps(spec, indent=1))
    return p


def a(cls, t0, t1, inner, anim="pop", style="", out="fade"):
    return f"<div class='a {cls}' data-t0='{t0}' data-t1='{t1}' data-in='{anim}' data-out='{out}' style='{style}'>{inner}</div>"


def pill(t0, t1, text, y=1230, kind="", anim="pop"):
    return a(f"pill {kind}", t0, t1, f"<span>{text}</span>", anim, f"top:{y}px")


L = "library/"
built = {}

# MON: self-check, POV/text-on-clip, no end card (~12 s)
dl = L + "bw-dorsiflexion-lunge.mp4"
built["mon-ankle-test"] = reel("mon-ankle-test", "mobility", [
    {"clip": dl, "start": 1.5, "dur": 3.0, "zoom": 1920, "cx": 0.5},
    {"clip": dl, "start": 4.5, "dur": 3.0, "zoom": 2300, "cx": 0.56},
    {"clip": dl, "start": 7.5, "dur": 3.0, "zoom": 1920, "cx": 0.5},
    {"clip": dl, "start": 10.5, "dur": 3.0, "zoom": 2300, "cx": 0.56},
], "".join([
    a("xb hook shadow", 0, 12, "Can your knee<br><span class='hl'>touch the wall?</span>", "none", out="none"),
    pill(1.6, 4.2, "Half-kneel facing a wall"),
    pill(4.2, 6.8, "Front toes 4 in / 10 cm away"),
    pill(6.8, 9.4, "Knee to wall. Heel stays down"),
    pill(9.4, 12.0, "Which side is tighter: L or R?", kind="acc"),
]))

# TUE: 3-clip fix montage, 1/3 from frame 1, short end card
built["tue-ankle-fixes"] = reel("tue-ankle-fixes", "mobility", [
    {"clip": L + "bw-seated-ankle-floss.mp4", "start": 1.0, "dur": 4.5, "zoom": 1500, "cx": 0.42},
    {"clip": L + "fr-calf.mp4", "start": 2.0, "dur": 4.5, "zoom": 1250, "cx": 0.5},
    {"clip": L + "bw-calf-raise-wclub.mp4", "start": 0.8, "dur": 4.5, "zoom": 1920, "cx": 0.5},
], "".join([
    a("xb hook shadow", 0, 13.5, "Failed the<br><span class='hl'>ankle test?</span>", "none", out="none"),
    a("count", 0, 4.5, "1/3", "none", "top:1080px"), a("count", 4.5, 9.0, "2/3", "pop", "top:1080px"),
    a("count", 9.0, 13.5, "3/3", "pop", "top:1080px"),
    pill(0, 4.5, "Seated ankle circles", 1230, anim="none"), pill(1.8, 4.5, "Heel down, slow circles", 1330, "dark"),
    pill(4.5, 9.0, "Foam roll calves", 1230), pill(6.3, 9.0, "Pause on tight spots", 1330, "dark"),
    pill(9.0, 13.5, "Calf raise + pause", 1230), pill(10.8, 13.5, "Big toe pressure, 2 s hold", 1330, "dark"),
]), end={"dur": 1.2, "cta": "Save this for tonight"})

# WED: tip of the week, clean loop, one line, no end card (~8 s)
built["wed-tip-midback"] = reel("wed-tip-midback", "rotation", [
    {"clip": L + "bw-kneeling-rotation.mp4", "start": 2.0, "dur": 8.0, "zoom": 1300, "cx": 0.5},
], "".join([
    a("kick", 0, 8, "TIP OF THE WEEK", "none", "top:230px", out="none"),
    a("xb hook shadow", 0, 8, "Turn your <span class='hl'>mid-back</span>,<br>not your low back", "none", "top:300px;font-size:96px", out="none"),
]))

# THU: power drill, step labels, short end card (~11 s)
lb = L + "bw-lateral-bound-to-stick.mp4"
built["thu-lateral-bound"] = reel("thu-lateral-bound", "power", [
    {"clip": lb, "start": 1.0, "dur": 5.5, "zoom": 1450, "cx": 0.52},
    {"clip": lb, "start": 6.5, "dur": 5.3, "zoom": 1300, "cx": 0.45},
], "".join([
    a("xb hook shadow", 0, 10.8, "Speed starts<br><span class='hl'>in the ground</span>", "none", out="none"),
    pill(0.9, 3.0, "Push off hard, land soft"),
    pill(3.0, 5.2, "Stick it for 2 seconds"),
    pill(5.2, 7.4, "Torso quiet, knee over toes"),
    pill(7.4, 10.8, "3 x 5 each way", kind="acc"),
]), end={"dur": 1.2, "cta": "Send this to your golf buddy"})

# FRI: motion-graphic myth vs fact, no end card (~15 s)
sq = L + "kb-front-rack-squat.mp4"
built["fri-knees-myth"] = reel("fri-knees-myth", "back", [
    {"clip": sq, "start": 4.5, "dur": 10.0, "zoom": 1920, "cx": 0.47},
    {"clip": sq, "start": 4.5, "dur": 5.0, "zoom": 2200, "cx": 0.47},
], "".join([
    a("shade", 0, 15, "", "none", out="none"),
    a("bar", 0, 15, "", "grow", out="none"),
    a("", 0, 15, "<span style='font-family:XB;font-size:58px;background:#E5484D;color:#fff;padding:4px 20px'>MYTH</span>", "none", "left:60px;top:250px", "none"),
    a("xb shadow", 0, 4.0, "Knees should<br>never go past<br>your toes", "none", "left:60px;right:60px;top:340px;font-size:118px"),
    a("", 2.0, 4.0, "", "wipe", "left:50px;width:760px;top:520px;height:14px;background:#E5484D"),
    a("", 4.0, 15, "<span style='font-family:XB;font-size:58px;background:var(--acc);color:#000;padding:4px 20px'>FACT</span>", "pop", "left:60px;top:250px", "none"),
    a("xb shadow", 4.0, 7.6, "Knees moving<br>forward is <span class='hl'>normal</span>", "up", "left:60px;right:60px;top:340px;font-size:110px"),
    a("sb shadow", 4.6, 7.6, "Squats, lunges, stairs, your golf posture: the knee travels forward when the ankle bends.", "up", "left:64px;right:90px;top:600px;font-size:44px;line-height:1.3"),
    a("xb shadow", 7.6, 11.2, "Holding them back<br>moves load to your<br><span class='hl'>hips + low back</span>", "up", "left:60px;right:60px;top:340px;font-size:100px"),
    a("sb", 8.2, 11.2, "Squat study: Fry et al., 2003", "fade", "left:64px;top:700px;font-size:36px;color:rgba(255,255,255,.75)"),
    a("cb", 11.2, 15, "DO THIS INSTEAD", "left", "left:64px;top:340px;font-size:60px;letter-spacing:4px;color:var(--acc)"),
    a("xb shadow", 11.4, 15, "✓ Heels down", "left", "left:60px;top:420px;font-size:96px"),
    a("xb shadow", 12.0, 15, "✓ Knee tracks over toes", "left", "left:60px;top:530px;font-size:96px"),
    a("xb shadow", 12.6, 15, "✓ Depth you control", "left", "left:60px;top:640px;font-size:96px"),
    a("sb", 13.2, 15, "Knee pain that sticks around? Get it checked.", "fade", "left:64px;top:780px;font-size:38px;color:rgba(255,255,255,.8)"),
]))

# SAT: strength/rotation, text-on-clip POV, offer end card (~10 s)
mb = L + "mb-bulgarian-split-squat-with-torso-rotation.mp4"
built["sat-split-squat-rotation"] = reel("sat-split-squat-rotation", "rotation", [
    {"clip": mb, "start": 6.0, "dur": 4.5, "zoom": 1920, "cx": 0.5},
    {"clip": mb, "start": 10.5, "dur": 4.5, "zoom": 2250, "cx": 0.5},
], "".join([
    a("xb hook shadow", 0, 9.0, "POV: your lead leg<br><span class='hl'>finally holds the turn</span>", "none", "font-size:92px", out="none"),
    pill(1.0, 3.0, "Drop straight down"),
    pill(3.0, 5.0, "Turn over the front hip"),
    pill(5.0, 7.0, "Chest tall, no wobble"),
    pill(7.0, 9.0, "3 x 6 each leg", kind="acc"),
]), end={"dur": 1.4, "cta": "PFG On Demand"})

if __name__ == "__main__":
    only = sys.argv[1:] or list(built)
    for k in only:
        r = subprocess.run([sys.executable, str(ROOT / "tools/overlay_reel.py"), str(built[k])], cwd=ROOT,
                           capture_output=True, text=True)
        print(k, r.stdout.strip(), r.stderr.strip()[-500:])
