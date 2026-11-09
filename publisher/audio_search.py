#!/usr/bin/env python3
"""Search Instagram's music library (Instagram Audio API) and save results to audio/.
No query = what Instagram returns as trending. Only tracks cleared for third-party use come back.
usage: audio_search.py [search words ...]"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_VERSION') or 'v23.0'}"
params = {"audio_type": "music", "user_id": os.environ["IG_USER_ID"], "access_token": os.environ["META_PAGE_TOKEN"]}
q = " ".join(sys.argv[1:]).strip()
if q:
    params["search_query"] = q
r = requests.get(f"{GRAPH}/ig_audio", params=params, timeout=60)
body = r.json()
out = Path(__file__).resolve().parent.parent / "audio"
out.mkdir(exist_ok=True)
name = "trending.json" if not q else "search-" + "-".join(q.lower().split())[:40] + ".json"
keep = ("audio_id", "title", "display_artist", "duration_in_ms", "is_ads_eligible", "on_platform_audio_preview_link")
result = {"searched_at": datetime.now(timezone.utc).isoformat(), "query": q or None}
if "error" in body:
    result["error"] = body["error"].get("message")
    print("✗", result["error"])
else:
    items = body.get("data", [])
    result["tracks"] = [{k: t.get(k) for k in keep} for t in items]
    print(f"✓ {len(items)} tracks")
    for t in result["tracks"][:15]:
        print(f"  {t['audio_id']}  {t['title']} — {t.get('display_artist')}  ({(t.get('duration_in_ms') or 0)//1000}s)")
(out / name).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
