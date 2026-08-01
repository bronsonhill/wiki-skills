#!/usr/bin/env python3
"""Fetch a YouTube transcript as timestamp-anchored markdown.

Usage:
    fetch_transcript.py <url> [<url> ...] --out-dir DIR [--chunk-seconds N]

Writes one `<video-id>.transcript.md` per URL into --out-dir and prints the
paths it wrote. Prefers human-authored captions over auto-generated ones.

YouTube's auto-caption VTT is heavily redundant: each cue repeats the tail of
the previous cue so captions can scroll. Naive parsing roughly doubles the
word count and wrecks the timestamps. `_merge` strips the inline karaoke
timing tags and removes that overlap.
"""

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# <00:00:01.359> and <c>...</c> karaoke tags inside auto-caption cues
TIMING_TAG = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>|</?c[^>]*>")
CUE_TIME = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(url):
    """Return (video_id, title, duration_seconds) for a URL."""
    r = run(["yt-dlp", "--skip-download", "--dump-json", "--no-warnings", url])
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata failed for {url}:\n{r.stderr.strip()}")
    meta = json.loads(r.stdout.splitlines()[0])
    return meta["id"], meta.get("title", meta["id"]), int(meta.get("duration") or 0)


def download_vtt(url, tmp):
    """Download the best available English VTT. Returns (path, is_auto)."""
    base = ["yt-dlp", "--skip-download", "--no-warnings", "--sub-format", "vtt",
            "--sub-langs", "en.*,en", "-o", str(tmp / "%(id)s.%(ext)s"), url]

    # Human-authored captions first: they carry real punctuation and casing,
    # which materially improves the digest.
    run(base[:1] + ["--write-sub"] + base[1:])
    manual = sorted(tmp.glob("*.vtt"))
    if manual:
        return manual[0], False

    run(base[:1] + ["--write-auto-sub"] + base[1:])
    auto = sorted(tmp.glob("*.vtt"))
    if auto:
        return auto[0], True
    return None, False


def parse_cues(path):
    """Yield (start_seconds, text) per cue, tags stripped, blanks dropped."""
    cues = []
    start = None
    buf = []

    def flush():
        if start is None:
            return
        text = " ".join(buf).strip()
        text = TIMING_TAG.sub("", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            cues.append((start, text))

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CUE_TIME.search(line)
        if m:
            flush()
            h, mi, s, ms = (int(x) for x in m.groups()[:4])
            start = h * 3600 + mi * 60 + s + ms / 1000
            buf = []
        elif start is not None and line.strip() and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            buf.append(line.strip())
    flush()
    return cues


def _merge(prev_words, new_words):
    """Append new_words to prev_words, dropping the repeated overlap.

    Auto-captions restate the tail of the previous cue at the head of the next.
    Find the longest suffix of prev that equals a prefix of new and return only
    the genuinely new remainder.
    """
    max_overlap = min(len(prev_words), len(new_words), 40)
    for n in range(max_overlap, 0, -1):
        if prev_words[-n:] == new_words[:n]:
            return new_words[n:]
    return new_words


def build_blocks(cues, chunk_seconds):
    """Collapse cues into timestamped blocks of ~chunk_seconds each."""
    words, blocks = [], []
    block_start = cues[0][0] if cues else 0
    block_words = []

    for start, text in cues:
        new = _merge(words, text.split())
        if not new:
            continue
        words.extend(new)
        if not block_words:
            block_start = start
        block_words.extend(new)
        if start - block_start >= chunk_seconds:
            blocks.append((block_start, " ".join(block_words)))
            block_words = []

    if block_words:
        blocks.append((block_start, " ".join(block_words)))
    return blocks, len(words)


def hhmmss(seconds):
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fetch(url, out_dir, chunk_seconds):
    vid, title, duration = probe(url)
    with tempfile.TemporaryDirectory() as td:
        vtt, is_auto = download_vtt(url, Path(td))
        if vtt is None:
            raise RuntimeError(f"No English captions available for {url}")
        cues = parse_cues(vtt)

    if not cues:
        raise RuntimeError(f"Captions for {url} parsed to zero cues")

    blocks, word_count = build_blocks(cues, chunk_seconds)

    lines = [
        "---",
        f"video_id: {vid}",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"url: {url}",
        f"duration: {hhmmss(duration)}",
        f"captions: {'auto-generated' if is_auto else 'human-authored'}",
        f"words: {word_count}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    for start, text in blocks:
        stamp = hhmmss(start)
        lines.append(f"**[{stamp}]({url}&t={int(start)}s)** {text}")
        lines.append("")

    out = Path(out_dir) / f"{vid}.transcript.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out, word_count, is_auto, duration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--chunk-seconds", type=int, default=45)
    args = ap.parse_args()

    failed = 0
    for url in args.urls:
        try:
            out, words, is_auto, duration = fetch(url, args.out_dir, args.chunk_seconds)
            kind = "auto" if is_auto else "manual"
            print(f"OK  {out}  ({words} words, {kind} captions, {hhmmss(duration)})")
        except Exception as e:  # noqa: BLE001 - report and continue to next URL
            failed += 1
            print(f"FAIL {url}: {e}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
