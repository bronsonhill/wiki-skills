#!/usr/bin/env bash
# build.sh — compile a practice-exam .tex to PDF and report results.
# Usage: build.sh path/to/exam.tex
# Runs pdflatex twice (so the exam class's marks totals + page refs resolve),
# captures errors from the log, and prints the output PDF path + page count.
set -uo pipefail

TEX="${1:?usage: build.sh path/to/exam.tex}"
[ -f "$TEX" ] || { echo "ERROR: no such file: $TEX" >&2; exit 1; }

DIR=$(cd "$(dirname "$TEX")" && pwd)
BASE=$(basename "$TEX" .tex)
cd "$DIR" || exit 1

run() { pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$BASE.tex" >/dev/null 2>&1; }

# First pass; if it fails, surface the real errors and stop.
if ! run; then
  echo "=== LaTeX FAILED — errors from $BASE.log ===" >&2
  grep -nE '^(.*:[0-9]+:|! )' "$BASE.log" | head -20 >&2
  exit 2
fi
# Second pass resolves \totalpoints / page totals. Don't fail the build on it.
run

PDF="$DIR/$BASE.pdf"
[ -f "$PDF" ] || { echo "ERROR: no PDF produced" >&2; exit 3; }

PAGES=$(pdfinfo "$PDF" 2>/dev/null | awk '/^Pages:/{print $2}')
echo "OK: $PDF (${PAGES:-?} pages)"
