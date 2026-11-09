#!/usr/bin/env python3
"""
PFG Auto-Poster — publishes queued posts to Instagram + Facebook Page.

How it works
  - Every post is one JSON file in queue/.
  - On each run, any post whose "publish_at" time has passed is published.
  - Successful posts move to posted/ (with the live post IDs).
  - Failed posts move to failed/ (with the error), so nothing retries forever.

Environment variables (set as GitHub Actions secrets)
  META_PAGE_TOKEN   long-lived Facebook Page access token (does not expire)
  FB_PAGE_ID        Facebook Page ID
  IG_USER_ID        Instagram Business/Creator account ID
  MEDIA_BASE_URL    public URL where media/ is hosted (GitHub Pages)
  GRAPH_VERSION     optional, e.g. v23.0
  DRY_RUN           optional, "1" = log what would post, change nothing
"""
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE, POSTED, FAILED = ROOT / "queue", ROOT / "posted", ROOT / "failed"

GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TOKEN = os.getenv("META_PAGE_TOKEN", "")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "").rstrip("/")
DRY_RUN = os.getenv("DRY_RUN", "") == "1"

VALID_TYPES = {"image", "reel", "carousel"}
VALID_PLATFORMS = {"instagram", "facebook"}
IG_CAPTION_MAX = 2200
IG_HASHTAG_MAX = 30


class PostError(Exception):
    pass


# ---------- helpers ----------

def log(msg):
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {msg}", flush=True)


def media_url(path_or_url):
    """Accept a full URL, or a path inside media/ (e.g. 'reels/hip-turn.mp4')."""
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    if not MEDIA_BASE_URL:
        raise PostError("MEDIA_BASE_URL is not set, so media paths can't be turned into public URLs")
    return f"{MEDIA_BASE_URL}/{path_or_url.lstrip('/')}"


def graph(method, endpoint, **params):
    params["access_token"] = TOKEN
    url = f"{GRAPH}/{endpoint}"
    for attempt in range(3):
        r = requests.request(method, url, data=params if method == "POST" else None,
                             params=params if method == "GET" else None, timeout=60)
        if r.status_code < 500:
            break
        time.sleep(5 * (attempt + 1))  # retry Meta server hiccups
    body = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", {})
        raise PostError(f"{endpoint}: {err.get('message', r.text)} (code {err.get('code')})")
    return body


def build_caption(post):
    caption = post["caption"].strip()
    tags = post.get("hashtags") or []
    if tags:
        caption += "\n\n" + " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
    return caption


def validate(post, name):
    problems = []
    for key in ("publish_at", "type", "caption", "media"):
        if key not in post:
            problems.append(f"missing '{key}'")
    if problems:
        return problems
    if post["type"] not in VALID_TYPES:
        problems.append(f"type must be one of {sorted(VALID_TYPES)}")
    try:
        when = datetime.fromisoformat(post["publish_at"])
        if when.tzinfo is None:
            problems.append("publish_at needs a timezone offset, e.g. 2026-11-02T07:30:00-05:00")
    except ValueError:
        problems.append("publish_at is not a valid ISO date/time")
    platforms = post.get("platforms", ["instagram", "facebook"])
    if not set(platforms) <= VALID_PLATFORMS or not platforms:
        problems.append(f"platforms must be from {sorted(VALID_PLATFORMS)}")
    media = post["media"]
    if post["type"] == "carousel":
        if not isinstance(media, list) or not 2 <= len(media) <= 10:
            problems.append("carousel media must be a list of 2–10 files")
    elif not isinstance(media, str):
        problems.append("media must be a single file path for image/reel posts")
    caption = build_caption(post)
    if len(caption) > IG_CAPTION_MAX:
        problems.append(f"caption + hashtags is {len(caption)} chars (Instagram max {IG_CAPTION_MAX})")
    if caption.count("#") > IG_HASHTAG_MAX:
        problems.append(f"more than {IG_HASHTAG_MAX} hashtags (Instagram limit)")
    return problems


# ---------- Instagram ----------

def ig_wait_until_ready(container_id, timeout=300):
    """Videos must finish processing before they can be published."""
    start = time.time()
    while time.time() - start < timeout:
        status = graph("GET", container_id, fields="status_code,status").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PostError(f"Instagram couldn't process the media (status {status})")
        time.sleep(10)
    raise PostError("Instagram media processing timed out")


def ig_container(url, kind, caption=None, child=False, audio=None):
    params = {}
    if kind == "video":
        params.update(media_type="REELS" if not child else "VIDEO", video_url=url)
        if not child:
            params["share_to_feed"] = "true"
            if audio:  # Instagram library music via the Instagram Audio API
                params["audio_configuration"] = json.dumps({k: v for k, v in audio.items()
                                                            if k in ("audio_id", "audio_volume", "video_volume")})
    else:
        params["image_url"] = url
    if child:
        params["is_carousel_item"] = "true"
    if caption:
        params["caption"] = caption
    cid = graph("POST", f"{IG_USER_ID}/media", **params)["id"]
    if kind == "video":
        ig_wait_until_ready(cid)
    return cid


def is_video(path):
    return path.lower().endswith((".mp4", ".mov"))


def publish_instagram(post):
    caption = build_caption(post)
    if post["type"] == "image":
        cid = ig_container(media_url(post["media"]), "image", caption)
    elif post["type"] == "reel":
        cid = ig_container(media_url(post["media"]), "video", caption, audio=post.get("audio"))
    else:  # carousel
        children = [ig_container(media_url(m), "video" if is_video(m) else "image", child=True)
                    for m in post["media"]]
        cid = graph("POST", f"{IG_USER_ID}/media", media_type="CAROUSEL",
                    children=",".join(children), caption=caption)["id"]
        ig_wait_until_ready(cid)
    return graph("POST", f"{IG_USER_ID}/media_publish", creation_id=cid)["id"]


# ---------- Facebook Page ----------

def publish_facebook(post):
    caption = post.get("facebook_caption") or build_caption(post)
    if post["type"] == "image":
        return graph("POST", f"{FB_PAGE_ID}/photos", url=media_url(post["media"]),
                     caption=caption)["id"]
    if post["type"] == "reel":
        return graph("POST", f"{FB_PAGE_ID}/videos", file_url=media_url(post["media"]),
                     description=caption)["id"]
    # carousel -> multi-photo post (FB doesn't take mixed video carousels via API)
    images = [m for m in post["media"] if not is_video(m)]
    if not images:
        raise PostError("Facebook multi-photo post needs at least one image")
    photo_ids = [graph("POST", f"{FB_PAGE_ID}/photos", url=media_url(m),
                       published="false")["id"] for m in images]
    attached = {f"attached_media[{i}]": json.dumps({"media_fbid": pid})
                for i, pid in enumerate(photo_ids)}
    return graph("POST", f"{FB_PAGE_ID}/feed", message=caption, **attached)["id"]


PUBLISHERS = {"instagram": publish_instagram, "facebook": publish_facebook}


# ---------- main loop ----------

def move(src, dest_dir, post):
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / src.name
    dest.write_text(json.dumps(post, indent=2, ensure_ascii=False) + "\n")
    src.unlink()


def run():
    if not DRY_RUN:
        missing = [k for k, v in {"META_PAGE_TOKEN": TOKEN, "FB_PAGE_ID": FB_PAGE_ID,
                                   "IG_USER_ID": IG_USER_ID}.items() if not v]
        if missing:
            log(f"Not set up yet (missing: {', '.join(missing)}). Nothing published.")
            return 0  # not an error until setup is finished

    now = datetime.now(timezone.utc)
    files = sorted(QUEUE.glob("*.json"))
    due, failures = 0, 0
    for f in files:
        try:
            post = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            log(f"✗ {f.name}: not valid JSON ({e})")
            failures += 1
            continue

        problems = validate(post, f.name)
        if problems:
            log(f"✗ {f.name}: " + "; ".join(problems))
            post["error"] = "; ".join(problems)
            if not DRY_RUN:
                move(f, FAILED, post)
            failures += 1
            continue

        if datetime.fromisoformat(post["publish_at"]) > now:
            continue
        due += 1

        platforms = post.get("platforms", ["instagram", "facebook"])
        results = post.setdefault("results", {})
        for platform in platforms:
            if results.get(platform, {}).get("id"):
                continue  # already went out on an earlier run
            if DRY_RUN:
                log(f"[dry run] would post {f.name} ({post['type']}) to {platform}")
                continue
            try:
                pid = PUBLISHERS[platform](post)
                results[platform] = {"id": pid, "at": datetime.now(timezone.utc).isoformat()}
                log(f"✓ {f.name} → {platform} (id {pid})")
            except (PostError, requests.RequestException) as e:
                results[platform] = {"error": str(e), "at": datetime.now(timezone.utc).isoformat()}
                log(f"✗ {f.name} → {platform}: {e}")

        if DRY_RUN:
            continue
        if all(results.get(p, {}).get("id") for p in platforms):
            move(f, POSTED, post)
        else:
            failures += 1
            move(f, FAILED, post)

    log(f"Checked {len(files)} queued post(s); {due} due; {failures} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
