# Reading Practice

A personal, minimal site for practising reading/verbal questions from standardized tests.
The owner is the only user. It is live at https://huellasenarena.github.io/reading-practice/
(GitHub repo `huellasenarena/reading-practice`, public, served by GitHub Pages from `main` /).

The `gh` CLI's local config still labels the account `JNS99` (the old username); the real owner is `huellasenarena`.

## Site

- Plain `index.html` + `style.css` + `app.js`, with no framework and no build step. Black and white, dark mode via `prefers-color-scheme`. No emojis or icons in the UI; controls are words.
- Layout is the owner's choice from the mockups ("option C", split screen). The passage and images are on the left and the question and choices on the right. Questions with no passage or image use a single centered column.
- The owner uses it mainly on an iPad, often as a home-screen app. The page itself never scrolls (`.app` is `100dvh`); the passage pane and the question pane each scroll on their own, with `overscroll-behavior: contain`. This replaced a sticky passage pane whose bottom was cut off behind Safari's toolbar. Below 720px everything stacks in one scrolling column.
- Behaviour:
  - Questions appear in random order via **Next**, with no question numbers.
  - Filters: test, type (grouped by section), "verbal only", "include done", "wrong only", "starred only" (includes done questions).
  - Answering only says **Yes.** / **No.** and never reveals the answer on its own. A wrong pick gets ✗ and the user can try again. Only the first try is recorded in progress. With no answer key, the answer is recorded as "unchecked".
  - After a try, a **Show explanation** / **Show answer** button reveals the answer, any `note` and the explanation. The Previous / Next / Show row sits right under the choices, and the explanation opens below it to keep mouse travel short. The owner asked for this.
  - **Previous** goes back through questions seen this visit (the `trail` in app.js), keeping each one's state. Keys: A–E to choose, → or Enter for next, ← for previous.
  - **star** link on each question (`rp-stars-v1`, id → time).
  - **history** in the footer lists the last 200 questions shown (`rp-history-v1`, newest first, across visits), with a **starred** tab listing every starred question. Each row opens its question.
  - **flag** link on each question (with an optional note) for answers or text the owner thinks are wrong. Flags are stored in localStorage `rp-flags-v1`. The footer's **export flags (N)** downloads `flags.json` (id, test, source, note, question excerpt, stored answer). To review, ask the owner for that file, check each flagged question against its source, and fix it in the extraction scripts rather than hand-editing `data/`.
  - Typed answers (CAT para jumble and odd sentence) use a text box. Comparison ignores case, spaces and punctuation.
  - Progress is saved in localStorage (`rp-progress-v1`, prefs in `rp-prefs-v1`), per device.
  - `#<question-id>` in the URL opens a specific question, and the hash is then cleared. The address bar is never set to the current question, so a home-screen icon or bookmark saves the plain site.
- Home screen and offline: `manifest.webmanifest` + `icons/` (drawn by `tools/icons.py`). `sw.js` is a service worker that answers every request from the network first (4 s timeout) and falls back to its cache. On each load the page asks it to download any data files and images that are not cached yet (about 15 MB). The footer shows "available offline" when that is done. No version number needs bumping: updates arrive on the next online load. Home-screen apps on iPadOS keep their own storage, separate from Safari's.
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

Run the scripts from `tools/` with the project's virtualenv (`.venv/`, git-ignored): `python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt`, then e.g. `cd tools && ../.venv/bin/python tsa.py`. The scripts are deterministic, so a rebuild with no script changes leaves `data/` and `img/` unchanged in git.

A hyphen that ends a PDF line is marked by the extractor (`mark_hyphen()` in `common.py`) and joined to the next word by `clean()`. A hyphen followed by a space inside a line is kept as printed (e.g. SAT's "the affix meng- among", "ninth- through eleventh-century").

| Script | Source | Notes |
|---|---|---|
| `lsat.py` | `~/Desktop/lsat 140/141/151/158.pdf` (LSAT Warthog printouts) | `lsat 151.pdf` is actually PrepTest 157. Answer key and per-choice explanations are included. |
| `sat.py` | `~/Downloads/questionbank-export-*.pdf` | See the SAT notes below. |
| `cat.py` | `sources/cat/<year>s<slot>.html` (2IIM pages the owner pasted) | See the CAT notes below. |
| `tsa.py` | `~/Downloads/TSA <year> Section 1.pdf` + `... Answer Key.pdf` | The 2019 key is `~/Downloads/580266-tsa-oxford-2019-section-1-answer-key-2.pdf`. See the TSA notes below. |
| `tage.py` | 4 PDFs in `~/Downloads` (FNEGE livret, Ecricome corrigé, TAGE Executive, `livret_tage_exec_n°2.pdf`) | See the TAGE MAGE notes below. |
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
- 2012–2014 use fonts with char codes shifted by 29; `decode()` handles this. Plain ALL-CAPS text ("BLANK PAGE") must not be shifted, and `ENCODED_PUNCT` maps the leftover ¶ µ ³ ´ ± \x83 to quotes, dashes and °.
- Critical Thinking vs Problem Solving is decided by regex on the stem, giving 25/25 per year.
- Figures and figure-only choices are cropped to `img/tsa/`. When a figure sits among the choices (charts as options), the whole block including the choices is cropped and the choice texts are left blank.

**TAGE MAGE (`tage.py`)**
- The first three PDFs go to `data/tage.json`, Executive n°2 to `data/tage-exec2.json`. As of 2026-09-26 the first three PDFs are no longer in `~/Downloads`; the script then skips `tage.json` and leaves it as committed.
- The Executive booklets have no section headings, so they use the hand-made `EXEC_SUBTESTS` maps (one per booklet) and `PASSAGE_STARTS`.
- Executive n°2 separates paragraphs with no vertical space; `_paragraphs()` ends a paragraph on a short justified line that ends a sentence.
- `KEY_FIXES` overrides wrong keys with a `note`: Executive n°2 Q23 (key D is the average of lap speeds; the right answer is C). Executive n°2 prints the same Conditions minimales question as both Q38 and Q57; both are kept.
- Non-verbal questions are cropped to images, rendered with `annots=False` (the livret PDF carries a previous owner's ink answer marks and highlights).
- The livret prints Logique 6–25 in two columns; `_columns()` reorders those lines and crops each question to its column.
- Fractions and exponents do not survive as text. Where they appear in the choices (small-size text, stacked fragments, or a formula piece on the choice row), the choices stay in the image and the text choices are blank. Where they appear in a Conditions minimales stem, the text stem is dropped because the image shows it.
- "A." only counts as a choice label at the start of a line ("… à 70 km de A. Quelle …" is not choice A).
- Conditions minimales get the standard A–E choices.
- The livret has no questions for Calcul 30, Raisonnement 14–15 or Logique 5; its key marks them "/".
- Explanations exist only for the Ecricome test.

**Puerto Rico LSAT (`lsat_pr.py`)**
- Merges overlapping screenshots: offsets are voted from identical lines, with a fuzzy fallback. When two copies of a line conflict, the one captured further from the screen edge is kept.
- Every RC question in a set gets the most complete copy of its passage.
- The answer keys in `KEYS` were read by hand from the LawHub review tables. Section 4's key came from screenshots the owner sent.
- The section 4 passage for questions 22–27 was completed from later screenshots in `sources/pr/extra/`. `pr_ocr.py extra` OCRs only that folder into `ocr.json` as `extra-<i>`, and `lsat_pr.py` merges those shots last.
- `page_lines()` drops the question-number row at the bottom of the screen and half-lines cut off at the screen edge. `OCR_FIXES` holds misreads that were checked against the screenshots. Other oddities, such as "explixaría", "per es una" and "podrían se", are in LawHub's own text and are kept.

## Status (2026-09-26)

- 2,839 questions, and every one has an answer. TAGE Executive n°2 (60) was added on 2026-09-26, after the answer-key check below.
- Stratified answer-key check (2026-09-24): 272 questions solved blind, 2–3 from every paper and section. No key errors were found. Every disagreement was re-checked and the key held: official livret grid for all 141 livret questions, Ecricome explanations, 2IIM source pages for CAT, and pixel measurement for TSA figures.
- The same check found broken text and images, all fixed in the scripts: TAGE livret Logique pairs, ink marks, answer grid in Q30, split stems, lost fractions; TSA blank pages, chart choices missing, 2012–2014 characters; PR truncated passage, OCR junk; line-break hyphens everywhere.
- Question types for non-SAT tests come from regexes on the stem wording, so a few may be misfiled.
- The Puerto Rico OCR occasionally drops an accent.
- Progress is per device only. If the owner wants syncing, the suggestion was a private GitHub Gist (or an export/import button).
