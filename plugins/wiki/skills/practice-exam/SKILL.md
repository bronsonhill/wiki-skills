---
name: practice-exam
description: >
  Generate a practice exam for a subject as a typeset PDF (LaTeX), with questions drawn
  from a personal wiki and, optionally, the format of one or more example exam PDFs the
  user supplies. Produces a question paper and an answer-key PDF. Use when the user
  wants to "make a practice exam", "generate a mock exam", "create exam questions as a
  PDF", "build a sample exam from the wiki", or "produce a LaTeX exam with an answer
  key".
---

# Practice Exam Generator

Builds a practice exam as a typeset PDF. Questions come from the wiki. The format
(sections, mark split, question types) follows any example exams the user supplies. The
output is a `.tex` file using the `exam` document class, compiled to PDF by `build.sh`.

Paths and naming come from the consuming repo's `.claude/wiki-schema.md` (the
configuration table is in `ingest`). This skill reads `wiki_root`, `derived_dir`,
`domains`, `subject` and `source_policy`. When `domains` is set, draw questions only
from pages whose `domain` matches the requested subject.

Compile with **`${CLAUDE_PLUGIN_ROOT}/skills/practice-exam/build.sh`**. It runs
`pdflatex` twice (the `exam` class needs the second pass for mark totals and
`Page X of N`), prints the relevant errors from the `.log` on failure, and prints the
PDF path and page count on success.

## Prerequisites

Check that TeX Live has the `exam` class; don't assume it:

```bash
kpsewhich exam.cls
```

If that prints nothing, the class is missing. Install `texlive-latex-extra
texlive-fonts-recommended` (Linux/apt) or MacTeX (macOS).

## Step 1: Gather content from the wiki

1. Read `<wiki_root>/index.md`, then the relevant section indexes, to find the source,
   concept and material pages that cover the requested topics.
2. Read those pages and pull out what can be examined: formulas, mechanisms, contrasts,
   worked procedures (e.g. the Game of Life update rule, Wolfram rule numbering).
   Concept pages keep formulas in a `## Formula` section as Obsidian `$...$` math, which
   works in LaTeX unchanged.
3. If the wiki doesn't cover a requested topic yet, tell the user and suggest ingesting
   a source. Don't invent exam material to fill the gap.

## Step 2: Copy the format of any example exams

Do this whenever the user supplies example exam PDFs. Extract their structure first:

```bash
pdftotext "path/to/example-exam.pdf" - | head -80
```

Match what you see: section names, marks per part, total marks, and how questions are
phrased. With no example, use the 3-section, 30-mark layout in the template.

**Take only the format from an example; every question must be new.** Copy the
sections, mark split, question types and tone. Reusing the example's scenarios or
numbers, even reworded, hands the student a copy of an exam they already have, when the
point is to face unseen questions in a familiar shape. For each question slot, choose a
different topic, or a different scenario or instance, from the one the example uses.
After drafting, compare each part against the example and replace any part that maps
onto an example part one-to-one.

Never copy an example exam's text into the wiki or into the output `.tex`. University
exam papers are under copyright, like lecture material, so this applies whatever
`source_policy` says. Read the example only to work out its structure.

## Step 3: Write the .tex

Copy the template, then replace its questions with ones grounded in the wiki:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/skills/practice-exam/exam-template.tex" "<topic>-practice-exam.tex"
```

The template's headers and title block contain `SUBJECT NAME` and `SUBJECT CODE`
placeholders. Fill them from the schema's `subject` key (and the subject code, if the
wiki records one). Don't compile while either placeholder remains.

Rules:
- Put marks on `\part[N]` **only**, never on `\question` as well. The `exam` class adds
  both into `\numpoints`, so marks in both places double the total. Write the
  question's subtotal into its text instead: `\question` then
  `\textbf{Text. [18 marks]}`. The class sums the parts into `\numpoints` by itself;
  don't total them by hand.
- Give every part a `\begin{solution}...\end{solution}` block. It is hidden in the
  question paper and shown only in the answer key.
- Keep math in `$...$` / `$$...$$`, and use `booktabs` (`\toprule`/`\midrule`) for
  tables and grids, as the template does.
- Base every question on material in `<wiki_root>/`. No invented facts.

## Step 4: Build both PDFs

Question paper (solutions hidden; `\printanswers` stays commented out):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/practice-exam/build.sh" "<topic>-practice-exam.tex"
```

Answer key (enable `\printanswers` in a separate file and build that):

```bash
sed 's/^% \\printanswers/\\printanswers/' "<topic>-practice-exam.tex" > "<topic>-practice-exam-answers.tex"
bash "${CLAUDE_PLUGIN_ROOT}/skills/practice-exam/build.sh" "<topic>-practice-exam-answers.tex"
```

On success the driver prints something like `OK: /…/exam.pdf (2 pages)`. On a LaTeX
error it prints `=== LaTeX FAILED ===` with the offending `file:line:` excerpts and
exits non-zero. Read those lines, fix the `.tex`, and rebuild.

## Step 5: Check the render

A clean compile can still produce broken math or tables, so render page 1 to an image
and look at it:

```bash
pdftoppm -png -r 80 -f 1 -l 1 "<topic>-practice-exam-answers.pdf" /tmp/exam-check
```

Then read `/tmp/exam-check-1.png`. Confirm the mark totals, solution boxes, formulas
and tables look right before handing the PDFs to the user.

## Gotchas

- **Marks on both `\question` and `\part` double `\numpoints`.** If the cover total is
  twice what you expected, a `\question` carrying `[N]` also has `\part[N]`s. Drop the
  question's bracket and move the subtotal into its text, as the template does.
- **The `exam` class needs two passes.** After one `pdflatex` run, mark totals and
  `Page X of N` are wrong. The driver runs twice; don't replace it with a single manual
  invocation.
- **The second pass must not hard-fail.** Mark totals reference a count written by the
  first pass, so with a fresh `.aux` the second pass can exit non-zero. The driver
  tolerates that and fails only if the PDF is missing. Keep that behaviour.
- **`\printanswers` toggling depends on line position.** The template ships the line as
  `% \printanswers`, and the `sed` matches only at the start of a line. If you reflow
  that line, the answer-key build comes out with no answers and no error.
- **Obsidian math is LaTeX already.** `$...$` from a concept page's `## Formula`
  section pastes straight in. Obsidian `[[wikilinks]]` are **not** LaTeX; strip them
  from question text.

## Troubleshooting

- `kpsewhich exam.cls` prints nothing → install `texlive-latex-extra` (Linux) or MacTeX.
- Driver prints `! Undefined control sequence` → a package macro is used without its
  `\usepackage`; check the preamble against the template.
- Driver prints `! Misplaced alignment tab character &` → an unescaped `&` in question
  text (use `\&`) or a malformed `tabular`.
- Math shows as raw `$x$` → you're looking at the `.tex`, not the `.pdf`; render it
  with `pdftoppm` as in Step 5.

## Output location and git

Exam `.tex` and `.pdf` files are study output, not wiki pages, so keep them out of
`<wiki_root>/`. Put them wherever the user is working (the repo root or a scratch
directory). Don't commit generated PDFs unless the user explicitly wants a shared bank
of practice exams.

## Bundled files

- `build.sh` compiles a `.tex` to PDF with two `pdflatex` passes, extracts log errors
  on failure, and prints the PDF path and page count.
- `exam-template.tex` is the starting skeleton, with the `\printanswers` toggle,
  solution blocks, a `booktabs` table and some math.
