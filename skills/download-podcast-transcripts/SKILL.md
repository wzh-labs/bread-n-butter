---
name: download-podcast-transcripts
description: Download transcripts for the latest episodes of a podcast hosted on YouTube. Use when the user asks to "download podcast transcripts", "get All-in transcripts", "fetch transcripts from a YouTube channel", "archive podcast captions", or similar. Defaults to the All-in Podcast (@allin) but works with any YouTube channel that posts full episodes.
---

# Download podcast transcripts from YouTube

Goal: pull plain-text transcripts for the latest N episodes of a podcast hosted on a YouTube channel into a local archive that re-runs only fetch new episodes. Optimized for podcast channels but works on any channel.

## Inputs

All optional:
- `channel` — YouTube handle (`@allin`), channel URL, or single video URL. Default: `@allin` (All-in Podcast). If a single video URL is given, only that episode is fetched.
- `N` — number of latest episodes to download (default 5, max 50).
- `since` — `YYYY-MM-DD`; download all episodes with `upload_date >= since`. Overrides `N` when provided.
- `min_duration_minutes` — drop entries shorter than this (default 10, to filter Shorts and trailers). Set to 0 to disable.

If the user names a podcast without giving a URL (e.g. "Acquired", "Lex Fridman"), do a quick web search to resolve the canonical YouTube channel handle and confirm before proceeding.

## Storage layout

Under `~/knowledge/podcasts/<channel-slug>/` (override with `$KNOWLEDGE_ROOT`):

```
<channel-slug>/
  index.json                              # all episodes ever indexed
  transcripts/
    <YYYY-MM-DD>-<videoid>.txt            # cleaned transcript
    <YYYY-MM-DD>-<videoid>.json           # episode metadata sidecar
```

`<channel-slug>` is the lowercased handle without `@` (e.g. `allin`). For channels without handles, use the channel ID slug yt-dlp returns (lowercased, prefix-stripped).

## Method

### 1. Verify yt-dlp is available

```bash
yt-dlp --version
```

If missing, tell the user to install it (`brew install yt-dlp` or `pip install yt-dlp`) and stop. Do not try to work around its absence.

### 2. List candidate videos

For a channel handle or URL, enumerate the Videos tab:

```bash
yt-dlp \
  --flat-playlist \
  --playlist-end <N or 50> \
  --print "%(id)s|%(upload_date)s|%(title)s|%(duration)s" \
  "https://www.youtube.com/<channel>/videos"
```

Notes:
- For a handle, the URL is `https://www.youtube.com/@<handle>/videos`. For a channel ID, `https://www.youtube.com/channel/<id>/videos`.
- yt-dlp's flat-playlist output is newest-first by upload date.
- Use `--playlist-end <N>` to stop yt-dlp from enumerating the entire channel — much faster.
- For `since` mode, set `--playlist-end 50` and filter the output to `upload_date >= since` after fetching.
- If the input is a single video URL, skip this step and treat that one video as the only candidate.

Drop candidates with `duration < min_duration_minutes * 60` to filter out Shorts.

### 3. Skip already-downloaded episodes

Load `index.json` (if present) and build a set of known video IDs. Drop any candidate whose ID is already indexed. If `index.json` doesn't exist yet, treat the set as empty.

### 4. Download metadata + auto-captions per new video

For each remaining candidate:

```bash
yt-dlp \
  --skip-download \
  --write-info-json \
  --write-sub --write-auto-sub \
  --sub-lang "en,en-US,en-GB" \
  --sub-format vtt \
  -o "<knowledge_root>/podcasts/<channel-slug>/_tmp/%(id)s" \
  "https://www.youtube.com/watch?v=<video-id>"
```

This writes `<videoid>.info.json` and `<videoid>.<lang>.vtt` into `_tmp/`. yt-dlp prefers manual subs over auto-generated when both exist. If no English captions exist for a video (rare on major podcast channels), log it and skip.

### 5. Convert VTT to clean plain text

Use the bundled helper:

```bash
uv run ~/.claude/skills/download-podcast-transcripts/clean_vtt.py \
  "<knowledge_root>/podcasts/<channel-slug>/_tmp/<videoid>.en.vtt" \
  > "<knowledge_root>/podcasts/<channel-slug>/transcripts/<YYYY-MM-DD>-<videoid>.txt"
```

The script strips WEBVTT headers, cue timings, inline `<00:00:00.000><c>` timing tags, and the rolling-window duplicates that YouTube auto-captions emit, leaving plain space-joined text.

If the VTT filename uses a regional variant (`en-US.vtt`, `en-GB.vtt`), pass that path instead.

### 6. Write the metadata sidecar

For each downloaded episode, write `<YYYY-MM-DD>-<videoid>.json` next to the `.txt`:

```json
{
  "video_id": "abc123",
  "title": "E218: Buffett retires, Tariff fallout, Anthropic raises",
  "channel": "allin",
  "upload_date": "2026-04-25",
  "duration_seconds": 5421,
  "url": "https://www.youtube.com/watch?v=abc123",
  "captions_source": "auto",
  "transcript_path": "transcripts/2026-04-25-abc123.txt",
  "downloaded_at": "2026-04-29"
}
```

Pull `title`, `upload_date`, and `duration` from `<videoid>.info.json`. Set `captions_source` to `manual` if `info_json["subtitles"]["en"]` (or any `en-*` variant) exists — that means yt-dlp downloaded a manually-uploaded track. Otherwise `auto`.

### 7. Update `index.json`

Schema:

```json
{
  "channel": "allin",
  "channel_url": "https://www.youtube.com/@allin",
  "episodes": [
    {
      "video_id": "abc123",
      "upload_date": "2026-04-25",
      "title": "E218: ...",
      "duration_seconds": 5421,
      "captions_source": "auto",
      "transcript_path": "transcripts/2026-04-25-abc123.txt"
    }
  ]
}
```

Sort `episodes[]` by `upload_date` descending. On re-run, merge: keep existing entries, prepend new ones.

### 8. Clean up `_tmp/`

After successful processing, remove `<channel-slug>/_tmp/`. On any failure, leave it in place so the user can inspect raw `.vtt` and `.info.json` files.

### 9. Commit and push

`~/knowledge` is a git repository. From `$KNOWLEDGE_ROOT` (default `~/knowledge`):

```bash
git add podcasts/<channel-slug>/
git commit -m "podcasts(<channel-slug>): <n> new episode(s) — <oldest-date>..<newest-date>"
git push
```

Rules:
- Stage only this channel's directory; never `git add -A`.
- No commit if no new transcripts were added.
- One commit per skill run.
- Transcripts run 50–200KB each — fine to commit. Don't gitignore `transcripts/`.
- If `git push` fails (no upstream, network, conflict), report it and stop. Do not force-push.

## Output

After the run, output a summary:

```
## Podcast Transcripts: <channel> (<YYYY-MM-DD>)

Downloaded <n> new episode(s):
- E218 — Buffett retires, Tariff fallout (2026-04-25, 90 min) → transcripts/2026-04-25-abc123.txt
- E217 — ... (2026-04-18, 88 min) → ...

Skipped <m> already-downloaded episode(s).
[Filtered <k> entries shorter than <min_duration_minutes> min.]
[Note any caption fetch failures.]
```

On the *first* run for a channel, append once:
- Auto-generated YouTube captions have no speaker labels.
- Timestamps are stripped from the cleaned transcript. If you need timed cues later, re-fetch with `yt-dlp --write-auto-sub` to get the original `.vtt`.

## Style rules

- Don't summarize, analyze, or quote the transcript content unless explicitly asked. This skill archives; it does not interpret.
- Always check `index.json` before fetching — never re-download an existing episode.
- Never delete or overwrite existing transcripts during a normal run.
- If `yt-dlp` returns a sign-in / age-gate / region error, surface the exact yt-dlp message and stop. Don't try cookie injection or proxies unless the user explicitly asks.
- If the channel resolves to multiple plausible matches (e.g. multiple "All-in" channels), confirm with the user before downloading.
