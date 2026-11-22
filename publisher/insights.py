#!/usr/bin/env python3
"""Pull Instagram stats for every post in posted/ and save them to insights/.

Writes insights/latest.json (one row per post + account totals) and a dated copy in insights/history/.
Each metric is requested on its own, so one metric Meta doesn't support for a post type never
blocks the rest; unsupported ones are listed under "unavailable".
Needs META_PAGE_TOKEN with instagram_manage_insights (+ IG_USER_ID).
"""
import json
from datetime import datetime, timezone

from publish import graph, PostError, IG_USER_ID, POSTED, ROOT, log

OUT = ROOT / "insights"
REEL = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
        "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate", "follows",
        "profile_visits"]
FEED = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
        "follows", "profile_visits"]


def metric(media_id, name):
    data = graph("GET", f"{media_id}/insights", metric=name).get("data", [])
    if not data:
        return None
    d = data[0]
    if "values" in d and d["values"]:
        return d["values"][0].get("value")
    return d.get("total_value", {}).get("value")


def main():
    rows, problems = [], []
    for f in sorted(POSTED.glob("*.json")):
        post = json.loads(f.read_text())
        mid = post.get("results", {}).get("instagram", {}).get("id")
        if not mid:
            continue
        row = {"post": f.stem, "type": post.get("type"), "music": post.get("music"),
               "publish_at": post.get("publish_at"), "ig_id": mid, "metrics": {}, "unavailable": []}
        for m in (REEL if post.get("type") == "reel" else FEED):
            try:
                v = metric(mid, m)
                if v is None:
                    row["unavailable"].append(m)
                else:
                    row["metrics"][m] = v
            except PostError as e:
                row["unavailable"].append(m)
                if "permission" in str(e).lower() or "(code 10)" in str(e) or "(code 190)" in str(e):
                    problems.append(f"{f.stem} {m}: {e}")
        ms = row["metrics"]
        if "ig_reels_avg_watch_time" in ms:  # Meta reports milliseconds
            ms["avg_watch_seconds"] = round(ms["ig_reels_avg_watch_time"] / 1000, 1)
        rows.append(row)
        log(f"{f.stem}: {', '.join(f'{k}={v}' for k, v in ms.items()) or 'no metrics'}")

    account = {}
    try:
        account = graph("GET", IG_USER_ID, fields="username,followers_count,media_count")
    except PostError as e:
        problems.append(f"account: {e}")

    now = datetime.now(timezone.utc)
    out = {"pulled_at": now.isoformat(), "account": account, "posts": rows, "problems": problems}
    OUT.mkdir(exist_ok=True)
    (OUT / "history").mkdir(exist_ok=True)
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    (OUT / "latest.json").write_text(text)
    (OUT / "history" / f"{now:%Y-%m-%d}.json").write_text(text)
    log(f"account: {account}")
    if problems:
        log("PROBLEMS:\n  " + "\n  ".join(problems[:10]))
        if all(not r["metrics"] for r in rows):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
