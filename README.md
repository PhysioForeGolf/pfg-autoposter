# PFG Auto-Poster

Free, hands-off Instagram + Facebook posting for Physio Fore Golf.
Runs on GitHub (free). No Posty, no monthly fee.

## How it works

```
Claude writes the week's posts ──► queue/  ──► GitHub checks every 15 min ──► Instagram + Facebook
Your videos/photos ──────────────► media/  ──► hosted publicly so Meta can download them
                                                   │
                                   posted/ ◄── success (with live post IDs)
                                   failed/ ◄── problem (with the error) + GitHub emails you
```

| Folder | What goes there |
|---|---|
| `queue/` | One `.json` file per upcoming post |
| `posted/` | Posts that went out (moved automatically) |
| `failed/` | Posts that hit an error (moved automatically) |
| `media/reels/`, `media/images/` | Your exercise videos and photos |
| `media/library.json` | Index of your media: exercise, focus tags, program, last posted |

Supported post types: **image**, **reel** (IG Reel + FB video), **carousel** (2–10 items; FB gets the photos as a multi-photo post).

---

## One-time setup (~45 min)

### Part 1 — Instagram + Facebook (10 min)
1. In the Instagram app: **Settings → Account type and tools** → make sure PFG is a **Professional** account (Creator or Business).
2. Link the Instagram account to the **PFG Facebook Page** (Meta Business Suite → Settings → Accounts → Instagram accounts → Connect).

### Part 2 — Meta developer app (15 min)
1. Go to **developers.facebook.com** → log in with the Facebook account that manages the PFG Page → **My Apps → Create App**.
2. Name it `PFG Auto-Poster`. Choose the **Business** app type (or the "Other" use case → Business). You do **not** need App Review — the app stays in Development mode and works on accounts you own.
3. Open **Tools → Graph API Explorer**:
   - **Meta App:** PFG Auto-Poster
   - **User or Page:** User Token
   - **Add permissions:** `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`
   - Click **Generate Access Token** → approve for the PFG Page and Instagram account.
4. Make it long-lived: copy the token → **Tools → Access Token Debugger** → paste → **Debug** → **Extend Access Token** → copy the new token.
5. Get the never-expiring **Page token**: back in Graph API Explorer, paste the extended token, run `GET me/accounts`. Find the PFG Page and copy its:
   - `access_token` → this is **META_PAGE_TOKEN**
   - `id` → this is **FB_PAGE_ID**
6. Confirm it never expires: paste META_PAGE_TOKEN into the Access Token Debugger → **Expires: Never**.
7. Get the Instagram ID: in Graph API Explorer (using META_PAGE_TOKEN) run
   `GET <FB_PAGE_ID>?fields=instagram_business_account` → the `id` inside is **IG_USER_ID**.

### Part 3 — GitHub (15 min)
1. Create a free account at **github.com** (if needed) → **New repository** → name `pfg-autoposter` → **Public** → Create.
   *Public is required for free media hosting. Your tokens stay private (stored as secrets). Only the queued captions and media are visible — the same content that's going on Instagram anyway.*
2. Upload everything in this folder (drag and drop works) → **Commit**.
3. **Settings → Pages → Source:** choose **GitHub Actions**.
4. **Settings → Secrets and variables → Actions**:
   - **Secrets** tab → New secret ×3: `META_PAGE_TOKEN`, `FB_PAGE_ID`, `IG_USER_ID`
   - **Variables** tab → New variable: `MEDIA_BASE_URL` = `https://<your-github-username>.github.io/pfg-autoposter`
5. **Actions** tab → enable workflows if prompted.

### Part 4 — Test (5 min)
1. **Actions → Weekly token health check → Run workflow.** Green ✓ with your Page name and IG username = connected.
2. Upload one real video to `media/reels/`, copy `examples/sample-reel-post.json` into `queue/`, point it at your video, and set `publish_at` a few minutes from now.
3. **Actions → Publish queued posts → Run workflow** with **Dry run** checked → confirm it says "would post".
4. Run it again without dry run → check Instagram and Facebook.

---

## Post file format

`queue/2026-11-02-0730-hip-turn-reel.json`
```json
{
  "publish_at": "2026-11-02T07:30:00-05:00",
  "type": "reel",
  "platforms": ["instagram", "facebook"],
  "media": "reels/half-kneeling-hip-turn.mp4",
  "caption": "Losing distance because your hips won't turn? ...",
  "hashtags": ["golffitness", "golftips", "physioforegolf"],
  "facebook_caption": "optional — different text for Facebook"
}
```
- `publish_at` needs the timezone offset: `-05:00` (EST, Nov–Mar) or `-04:00` (EDT, Mar–Nov).
- `platforms` is optional (defaults to both).
- `media` can be a path inside `media/` or any public URL.

## Media rules
- **Reels:** vertical 9:16 MP4 (H.264), under 100 MB (GitHub's file limit).
- **Images:** JPG. Instagram only accepts aspect ratios between 4:5 and 1.91:1.
- Max 30 hashtags, 2,200 characters per caption.

## When something fails
- GitHub emails you. Open `failed/<post>.json` → the `results` section shows the error.
- Fix it and move the file back into `queue/`. Platforms that already succeeded are skipped, so nothing double-posts.
- Health check fails on a Sunday → token stopped working (usually a Facebook password change). Repeat Part 2, steps 3–6, and update the `META_PAGE_TOKEN` secret.

## Video library (`library/`)

All 218 PFG exercise videos as clean Reel masters: logo intro/outro trimmed, square crop that follows the athlete, H.264.
`library/index.json` lists each clip with its exercise name, coaching notes and when it was last posted.
Finished posts are rendered from these with `tools/post_reel.py` (hook, coaching cues, colour per topic, PFG logo end card) and saved to `media/<week>/`.

## Content style rules (from Jim, Nov 2026)

Jim's feedback: the feed looked like one template with new content spliced in. Keep the brand in a few constants and vary everything else.

**Keep constant:** fonts (Barlow Condensed / Barlow), dark background with the yellow/green/theme accents, the PFG name on screen, plain-spoken evidence-based voice, caption structure (hook, ✅/❌ lines, one CTA, website line, 5–6 hashtags).

**Rotate every week, never the same format two posts in a row:**
- Reels: (a) clean clip: full-screen footage, one short line of text, no title block, no end card, loops; (b) step-label Reel (`post_reel.py --layout big`); (c) motion graphic (animated text/diagram, like the Nov 21 lifting-myth sample); (d) wrong vs right split screen; (e) POV / text-on-clip; (f) 3-clip montage. Use the logo end card on at most half the Reels.
- Hooks: rotate question / bold claim / number / POV / short story. Lengths: mix 6–8 s loops with 15–30 s teaching Reels.
- Carousels and the tip image: rotate photo-led, text-only "note" style, checklist, before/after. Not the same cover layout as the week before.
- Timely angles when they fit (holidays, winter/indoor training, majors on TV).
- No recordings from Jim/Ben yet (planned later). No AI-generated people.

**Grid covers:** every Reel gets a `cover` image made with `tools/make_cover.py` (set `"cover": "<date>/<name>-cover.jpg"` in the post JSON). Rotate `--style photo|split|type` so neighbouring grid tiles differ. Without a cover the publisher uses a frame 1 s in (`thumb_offset`), never the logo end card.

**Insights, 30 days to Nov 22 (from Jim's dashboard):** 3,191 views, 1,303 viewers. Reels ~3K views (mostly non-followers) vs posts 171; interactions Reels 54 vs posts 1. 25 profile visits, 2 bio-link taps. Every Reel lands at 220–520 views (Instagram's test audience) and none broke out. Landmine Reel: **average watch time 2 s**, 0 follows. Top: turn-test fixes 522, turn test 462, turn from hips 425, arms stealing speed 397 (3 sends).

**Watch-time rules (the #1 fix):** people decide in the first 1–2 s.
- Frame 1 is the movement, full screen, already in motion. No branded header, badge or title card at the start; the PFG name can sit small at the bottom.
- The hook is 3–7 words burned onto the footage, a curiosity gap or call-out ("This is why your back hurts after golf", "Your hips are why you slice"), visible from frame 1.
- Trim clips so action starts at 0.0 s (library masters often open at rest). Prefer 7–12 s Reels that loop; teaching Reels max ~20 s.
- Change something on screen every 1.5–2 s (cut, zoom, new label).
- End card on at most half the Reels; when used, keep it under 1.5 s.
- Mix: at least 5 Reels a week; the Wednesday tip becomes a short Reel; keep at most 1–2 carousels.

**What's working (views, week of Nov 9–20):** Reels 216–521 views; carousels 30–71; tip image 27. Lean on Reels; turn myth carousels into motion-graphic Reels.
