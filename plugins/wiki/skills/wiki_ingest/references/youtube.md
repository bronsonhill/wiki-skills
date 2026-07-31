# Transcribing YouTube-hosted sources

Read this only when the source is a YouTube video. Other hosts are covered in
`SKILL.md` Step 2.

## Clean the URLs first

Strip tracking parameters (`&embeds_referring_origin=…`, `&source_ve_path=…`) down to
the bare `https://www.youtube.com/watch?v=<id>` before passing anything to the script.
If the user points at a file of links rather than pasting them, read the file.

A single lecture is often several short videos plus one deck. Fetch them together and
treat them as one source, not one source per video.

## Fetch

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/wiki_ingest/scripts/fetch_transcript.py" \
  "<url>" "<url>" ... --out-dir <transcript-dir>
```

Writes one `<video-id>.transcript.md` per video: YAML frontmatter (title, duration,
caption kind, word count) then timestamp-anchored paragraphs, each stamp a clickable
deep link into the video. `--chunk-seconds N` (default 45) controls paragraph
granularity.

See `SKILL.md` Step 2 for where `<transcript-dir>` should point — it depends on
`source_policy`, and under `link-only` transcripts must not land in the repo.

## Verify the dedupe worked

The script prefers human-authored captions and falls back to auto-generated. YouTube's
auto-caption VTT repeats the tail of each cue so captions can scroll, so the script
strips that overlap. Sanity check the reported rate: **~130–160 wpm is right**. ~300 wpm
means the dedupe failed, and both the word count and the timestamps are then wrong.
Investigate before continuing.

> [!warning] Auto-captions mangle technical terms and names
> Observed in practice: "Ni Povitzki" → Nir Lipovetzky, "dharmmouth" → Dartmouth,
> "peratron" → Perceptron, "polomial" → polynomial. **The slides are ground truth**
> for all names, notation, and terminology. Never propagate a transcript spelling of a
> technical term into a wiki page without checking it against the deck. When a term
> appears only in the transcript, flag it as `(sp?)` rather than guessing.
