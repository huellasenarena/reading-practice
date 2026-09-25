# Reading Practice

A minimal site for practising reading and verbal-reasoning questions from standardized tests.
It shows one random question at a time. The passage is on the left and the question on the right.
Pick an answer to see whether it is correct, plus the explanation when the source has one.

Filters: test, question type, verbal only, include done, wrong only. Progress (done / correct / incorrect)
is stored in the browser's localStorage, so it is per device.

## Contents

| Test | Questions | Answer key | Explanations | Types |
|---|---|---|---|---|
| LSAT (PrepTests 140, 141, 157, 158) | 416 | yes | yes | Logical Reasoning and Reading Comprehension subtypes |
| LSAT – Puerto Rico PrepTest (Spanish) | 104 | yes | no | same subtypes |
| SAT Reading and Writing question bank (Hard) | 610 | yes | yes | College Board skills |
| CAT VARC 2017–2025 | 608 | yes | no | RC, para summary, para jumble, odd sentence, sentence placement |
| Oxford TSA Section 1, 2008–2022 | 750 | yes | no | Critical Thinking subtypes, Problem Solving |
| TAGE MAGE (French) | 291 | yes | Ecricome test only | the six sous-tests |

Question types were assigned by the extraction scripts from the wording of each question (except SAT,
whose export is already tagged), so a few may be misfiled.

## Non-verbal questions

Math, logic and data questions (TSA Problem Solving; TAGE MAGE Calcul, Conditions minimales and Logique)
are kept for now and marked `"verbal": false` in the data. The **verbal only** checkbox hides them.
To remove them for good:

```sh
python3 tools/drop_nonverbal.py           # dry run
python3 tools/drop_nonverbal.py --apply
```

## Data

`data/<source>.json` holds a list of questions; `data/index.json` lists the files the site loads.
Fields: `id`, `test`, `source`, `section`, `type`, `verbal`, `passage`, `question`, `choices`,
`answer` (a letter, or text for typed answers), and optionally `explanation`, `image`, `lang`, `note`.
Text uses blank lines between paragraphs, `**bold**`, `*italic*` and `++underline++`.

## Rebuilding the data

The scripts in `tools/` rebuild `data/` and `img/` from the original PDFs and pages. The sources
are not in the repo; they are expected in `~/Downloads`, `~/Desktop` and `sources/`.

```sh
pip install -r tools/requirements.txt
cd tools
python3 lsat.py; python3 sat.py; python3 cat.py; python3 tsa.py; python3 tage.py
python3 pr_ocr.py; python3 pr_stem_ocr.py; python3 lsat_pr.py   # OCR needs macOS
```

## Running locally

```sh
python3 -m http.server
```

Then open http://localhost:8000.
