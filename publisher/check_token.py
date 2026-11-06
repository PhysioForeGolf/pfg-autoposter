#!/usr/bin/env python3
"""Weekly health check: confirms the Meta token still works for both accounts.
If it fails, the GitHub Action fails and GitHub emails you."""
import os
import sys

import requests

GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_VERSION', 'v23.0')}"
TOKEN = os.environ["META_PAGE_TOKEN"]
checks = {
    "Facebook Page": (os.environ["FB_PAGE_ID"], "name"),
    "Instagram account": (os.environ["IG_USER_ID"], "username"),
}
ok = True
for label, (obj_id, field) in checks.items():
    r = requests.get(f"{GRAPH}/{obj_id}", params={"fields": field, "access_token": TOKEN}, timeout=30)
    data = r.json()
    if "error" in data:
        ok = False
        print(f"✗ {label}: {data['error'].get('message')}")
    else:
        print(f"✓ {label}: {data.get(field)}")

# Instagram allows a limited number of API posts per 24h; show remaining usage.
r = requests.get(f"{GRAPH}/{os.environ['IG_USER_ID']}/content_publishing_limit",
                 params={"fields": "quota_usage,config", "access_token": TOKEN}, timeout=30)
if r.ok and r.json().get("data"):
    d = r.json()["data"][0]
    print(f"ℹ Instagram posts used in last 24h: {d.get('quota_usage')} of {d.get('config', {}).get('quota_total')}")

sys.exit(0 if ok else 1)
