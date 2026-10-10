# Transcribing YouTube-hosted sources

Read this only when the source is a YouTube video. `SKILL.md` Step 2 covers other hosts.

## Clean the URLs first

Strip tracking parameters (`&embeds_referring_origin=…`, `&source_ve_path=…`) down to
the bare `https://www.youtube.com/watch?v=<id>` before passing anything to the script.
If the user points at a file of links instead of pasting them, read the file.

One lecture is often several short videos plus one deck. Fetch them together and
ingest them as a single source.

## Fetch

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/ingest/scripts/fetch_transcript.py" \
  "<url>" "<url>" ... --out-dir <transcript-dir>
```

The script writes one `<video-id>.transcript.md` per video: YAML frontmatter (title,
duration, caption kind, word count), then paragraphs that each open with a timestamp
linking into the video. `--chunk-seconds N` (default 45) sets paragraph length.

`SKILL.md` Step 2 says where `<transcript-dir>` should point. It depends on
`source_policy`; under `link-only`, transcripts must stay out of the repo.

## Check the dedupe

The script uses human-authored captions when they exist and falls back to
auto-generated ones. YouTube's auto-caption VTT repeats the tail of each cue so the
captions can scroll, and the script strips that overlap. Check the speaking rate it
reports: **130–160 wpm is normal**. Around 300 wpm means the dedupe failed, and both
the word count and the timestamps are wrong. Find out why before continuing.

> [!warning] Auto-captions mangle technical terms and names
> Seen in real transcripts: "Ni Povitzki" for Nir Lipovetzky, "dharmmouth" for
> Dartmouth, "peratron" for Perceptron, "polomial" for polynomial. **The slides are the
> authority** on names, notation and terminology. Check every technical term against
> the deck before it goes into a wiki page. When a term appears only in the transcript,
> mark it `(sp?)` instead of guessing.
