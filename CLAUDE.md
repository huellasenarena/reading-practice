# Reading Practice

A personal, minimal site for practising reading/verbal questions from standardized tests.
The owner is the only user. It is live at https://huellasenarena.github.io/reading-practice/
(GitHub repo `huellasenarena/reading-practice`, public, served by GitHub Pages from `main` /).

The `gh` CLI's local config still labels the account `JNS99` (the old username); the real owner is `huellasenarena`.

## Site

- Plain `index.html` + `style.css` + `app.js`, with no framework and no build step. Black and white, dark mode via `prefers-color-scheme`.
- Layout is the owner's choice from the mockups ("option C", split screen). The passage and images are on the left and the question and choices on the right. Questions with no passage or image use a single centered column.
- Behaviour:
  - Questions appear in random order via **Next**, with no question numbers.
  - Filters: test, type (grouped by section), "verbal only", "include done", "wrong only".
  - Answering only says **Yes.** / **No.** and never reveals the answer on its own. A wrong pick gets ✗ and the user can try again. Only the first try is recorded in progress. With no answer key, the answer is recorded as "unchecked".
  - After a try, a **Show explanation** / **Show answer** button reveals the answer, any `note` and the explanation. The Previous / Next / Show row sits right under the choices, and the explanation opens below it to keep mouse travel short. The owner asked for this.
  - **Previous** goes back through questions seen this visit (the `trail` in app.js), keeping each one's state. Keys: A–E to choose, → or Enter for next, ← for previous.
  - **flag** link on each question (with an optional note) for answers or text the owner thinks are wrong. Flags are stored in localStorage `rp-flags-v1`. The footer's **export flags (N)** downloads `flags.json` (id, test, source, note, question excerpt, stored answer). To review, ask the owner for that file, check each flagged question against its source, and fix it in the extraction scripts rather than hand-editing `data/`.
  - Typed answers (CAT para jumble and odd sentence) use a text box. Comparison ignores case, spaces and punctuation.
  - Progress is saved in localStorage (`rp-progress-v1`, prefs in `rp-prefs-v1`), per device.
  - `#<question-id>` in the URL opens a specific question.
- The app loads `data/index.json`, then every `data/<name>.json` listed in it.
- Test locally with `python3 -m http.server`.

## Data format

Each file in `data/` is a list of questions:
`id, test, source, section, type, verbal, passage, question, choices, answer`, plus optional `explanation, image (string or list), lang ("fr"/"es"), note`.

- `answer` is a letter, or the text to type when there are no `choices`.
- Text markup: paragraphs are separated by blank lines, plus `**bold**`, `*italic*` and `++underline++`. `app.js` escapes HTML and then applies this markup.
- Passages with several questions: each question carries its own full copy of the passage. The owner decided to leave it this way. A "keep passage sets together" mode was offered but not requested.

## Non-verbal questions

TSA Problem Solving and TAGE MAGE Calcul / Conditions minimales / Logique are included but marked `"verbal": false`. The owner may remove them later. `python3 tools/drop_nonverbal.py --apply` removes them and their orphaned images.

## Sources and extraction (`tools/`)

Python scripts rebuild `data/` and `img/`. PyMuPDF is used for PDFs, BeautifulSoup for CAT, and macOS Vision via `ocrmac` for the screenshots. `tools/common.py` has `write()`, which also regenerates `data/index.json`, and `save_png()`, which quantizes images.

Originals are not committed: `sources/` is git-ignored, and the PDFs live in `~/Downloads` and `~/Desktop`.

| Script | Source | Notes |
|---|---|---|
| `lsat.py` | `~/Desktop/lsat 140/141/151/158.pdf` (LSAT Warthog printouts) | `lsat 151.pdf` is actually PrepTest 157. Answer key and per-choice explanations are included. |
| `sat.py` | `~/Downloads/questionbank-export-*.pdf` | See the SAT notes below. |
| `cat.py` | `sources/cat/<year>s<slot>.html` (2IIM pages the owner pasted) | See the CAT notes below. |
| `tsa.py` | `~/Downloads/TSA <year> Section 1.pdf` + `... Answer Key.pdf` | The 2019 key is `~/Downloads/580266-tsa-oxford-2019-section-1-answer-key-2.pdf`. See the TSA notes below. |
| `tage.py` | 3 PDFs in `~/Downloads` (FNEGE livret, Ecricome corrigé, TAGE Executive) | See the TAGE MAGE notes below. |
| `pr_ocr.py`, `pr_stem_ocr.py`, `lsat_pr.py` | `~/Desktop/puerto rico.pdf` + `rest of pr lsat.pdf` (LawHub screenshots, Spanish) | See the Puerto Rico notes below. |

**SAT (`sat.py`)**
- Drops the 0.2pt spaces that split "rt" ligatures ("repor ted").
- Detects underlines and bullets from drawings.
- Crops charts and tables into `img/sat/`.
- Types are the College Board skills.

**CAT (`cat.py`)**
- Passages attach to the questions that follow them.
- Where the key's letter contradicts the choice text it quotes, the text wins and a `note` is added.
- There are no explanations.

**TSA (`tsa.py`)**
- 2012–2014 use fonts with char codes shifted by 29; `decode()` handles this.
- Critical Thinking vs Problem Solving is decided by regex on the stem, giving 25/25 per year.
- Figures and figure-only choices are cropped to `img/tsa/`.

**TAGE MAGE (`tage.py`)**
- The Executive booklet has no section headings, so it uses the hand-made `EXEC_SUBTESTS` map and `PASSAGE_STARTS`.
- Non-verbal questions are cropped to images.
- Conditions minimales get the standard A–E choices.
- The livret has no questions for Calcul 30, Raisonnement 14–15 or Logique 5; its key marks them "/".
- Explanations exist only for the Ecricome test.

**Puerto Rico LSAT (`lsat_pr.py`)**
- Merges overlapping screenshots: offsets are voted from identical lines, with a fuzzy fallback. When two copies of a line conflict, the one captured further from the screen edge is kept.
- Every RC question in a set gets the most complete copy of its passage.
- The answer keys in `KEYS` were read by hand from the LawHub review tables. Section 4's key came from screenshots the owner sent.

## Status (2026-09-24)

- 2,779 questions, and every one has an answer.
- 16 randomly sampled keys were checked by solving the questions; all were correct.
- Question types for non-SAT tests come from regexes on the stem wording, so a few may be misfiled.
- The Puerto Rico OCR occasionally drops an accent.
- Possible next step, not yet done: a stratified answer-key check of about 150 questions (2–3 from every paper, start/middle/end), emphasising TSA, TAGE MAGE, LSAT Puerto Rico and CAT, whose keys are separate from the questions. Report mismatches before changing any data.
- Progress is per device only. If the owner wants syncing, the suggestion was a private GitHub Gist (or an export/import button).
