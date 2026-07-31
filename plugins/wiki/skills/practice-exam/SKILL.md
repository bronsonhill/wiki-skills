---
name: practice-exam
description: >
  Generate a practice exam as a typeset PDF (LaTeX) for CMAS, drawing questions
  from the wiki (wiki/) and, optionally, mimicking the style/structure
  of one or more example exam PDFs the user supplies. Use when the user wants to
  "make a practice exam", "generate a mock exam", "create exam questions as a PDF",
  "build a sample exam from the wiki", or "produce a LaTeX exam with an answer key".
  Produces both a question paper and an answer-key PDF.
---

# Practice Exam Generator

Builds a practice exam as a typeset PDF. Question *content* comes from the CMAS
wiki (`wiki/`); the *format* (sections, mark weighting, question types)
is mimicked from example exam PDFs when the user supplies them. Output is a LaTeX
`.tex` using the `exam` document class, compiled to PDF by the driver.

The interaction surface is the LaTeX→PDF compile. **The driver is
`.claude/skills/practice-exam/build.sh`** — it runs `pdflatex` twice (so the `exam`
class resolves mark totals and `Page X of N`), surfaces real errors from the `.log`
on failure, and prints the PDF path + page count.

## Prerequisites

TeX Live with the `exam` class (verify, do not assume):

```bash
kpsewhich exam.cls
```

If empty, the class is missing — install `texlive-latex-extra texlive-fonts-recommended`
(Linux/apt) or MacTeX (macOS).

## Step 1 — Gather content from the wiki

1. Read `wiki/index.md` first to navigate, then the relevant section indexes.
   Identify the source pages / concepts / materials that cover the requested topics.
2. Read those pages. Pull the *examinable* material: formulas, mechanisms,
   contrasts, worked procedures (e.g. the Game of Life update rule, Wolfram rule
   numbering). Concept pages have a `## Formula` section in Obsidian `$...$` math —
   reuse it directly in LaTeX.
3. If a requested topic isn't yet covered in `wiki/`, say so rather than
   inventing exam-worthy claims — suggest ingesting a source first.

## Step 2 — Mimic the example exam(s) (optional but preferred)

If the user supplies example exam PDF(s), extract their structure first:

```bash
pdftotext "path/to/example-exam.pdf" - | head -80
```

Match what you observe: section names, per-part mark allocations, total marks, and
question phrasing style. If no example is given, default to the 3-section /
30-mark shape baked into the template.

**Use the example for *format only* — the questions must be NEW.** Copy the
structure (sections, mark split, question types, tone), never the questions
themselves. Transcribing the example's scenarios or numbers — even lightly
reworded — produces a duplicate of an exam the student already has, defeating the
purpose (they should face unseen questions in a familiar shape). For each question
slot, pick a *different* examinable topic or a *different* scenario/instance than
the example uses. After drafting, diff your questions against the example: if any
part maps 1:1 onto an example part, replace it.

Never copy the example exam's own text into `wiki/` or into the output `.tex` —
university exam papers are copyright, same as lecture material (see
`.claude/wiki-schema.md`). Read it only to infer structure.

## Step 3 — Author the .tex

Copy the template and replace the questions with wiki-grounded ones:

```bash
cp .claude/skills/practice-exam/exam-template.tex "<topic>-practice-exam.tex"
```

Rules:
- Put marks on `\part[N]` **only**, never on `\question` as well — the `exam`
  class adds both into `\numpoints`, so points on both double-counts the total.
  Write the question subtotal into the title text instead:
  `\question` then `\textbf{Text. [18 marks]}`. The class still sums the parts
  into `\numpoints` automatically — do not hand-total.
- Put a `\begin{solution}...\end{solution}` block in every part. It is hidden in
  the question paper and shown only in the answer key.
- Keep math in `$...$` / `$$...$$`; use `booktabs` (`\toprule`/`\midrule`) for
  tables/grids, as in the template.
- Ground every question in real `wiki/` material — no invented facts.

## Step 4 — Build both PDFs

Question paper (solutions hidden — `\printanswers` stays commented):

```bash
bash .claude/skills/practice-exam/build.sh "<topic>-practice-exam.tex"
```

Answer key (enable `\printanswers`, build a separate file):

```bash
sed 's/^% \\printanswers/\\printanswers/' "<topic>-practice-exam.tex" > "<topic>-practice-exam-answers.tex"
bash .claude/skills/practice-exam/build.sh "<topic>-practice-exam-answers.tex"
```

The driver prints e.g. `OK: /…/exam.pdf (2 pages)`. On a LaTeX error it prints
`=== LaTeX FAILED ===` with the offending `file:line:` excerpts and exits
non-zero — read those lines, fix the `.tex`, rebuild.

## Step 5 — Verify the render (don't skip)

Rasterize page 1 and actually look at it — a clean compile can still mis-render
math or tables:

```bash
pdftoppm -png -r 80 -f 1 -l 1 "<topic>-practice-exam-answers.pdf" /tmp/exam-check
```

Then read `/tmp/exam-check-1.png`. Confirm marks totals, solution boxes, and any
formulas/tables look right before handing back to the user.

## Gotchas

- **Points on both `\question` and `\part` double-count `\numpoints`.** If the
  cover total looks twice what you intended, you put `[N]` on a `\question` that
  also has `\part[N]`s. Drop the question's bracket and move the subtotal into its
  title text. The template does this already.
- **`exam` class needs two passes.** Mark totals and `Page X of N` are wrong after
  one `pdflatex` run. The driver runs twice — don't shortcut it with a single
  manual invocation.
- **Second pass must not hard-fail.** Mark totals reference a count written by
  pass 1, so a fresh `.aux` can make pass 2 noisy; the driver tolerates a pass-2
  non-zero exit and only fails if the PDF is missing. Keep that behavior.
- **`\printanswers` toggling is line-anchored.** The template ships the line as
  `% \printanswers`. The `sed` only matches at line start — if you reflow that
  line, the answer-key build silently stays blank.
- **Obsidian math is LaTeX-native.** `$...$` from concept pages' `## Formula`
  sections pastes straight in. But Obsidian `[[wikilinks]]` are **not** LaTeX —
  strip them from question text.

## Troubleshooting

- `kpsewhich exam.cls` empty → install `texlive-latex-extra` (Linux) / MacTeX.
- Driver prints `! Undefined control sequence` → a package macro used without its
  `\usepackage`; check the preamble matches the template.
- Driver prints `! Misplaced alignment tab character &` → an unescaped `&` in
  question text (use `\&`) or a malformed `tabular`.
- PDF builds but math looks like raw `$x$` → you're viewing the `.tex`, not the
  `.pdf`; rasterize with `pdftoppm` as in Step 5.

## Output location and git

Generated exam `.tex`/`.pdf` files are study artefacts, not wiki content — don't
put them under `wiki/`. Keep them wherever the user is working (e.g. repo root
or a scratch dir) and don't commit generated PDFs to the repo unless the user
explicitly wants a shared practice-exam bank.

## The driver

`.claude/skills/practice-exam/build.sh` — compiles a `.tex` to PDF (two `pdflatex`
passes), extracts log errors on failure, prints PDF path + page count.
`exam-template.tex` — the starting CMAS-shaped exam with the `\printanswers`
toggle, solution blocks, a `booktabs` table, and math.
