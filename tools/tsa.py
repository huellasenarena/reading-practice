"""Oxford TSA Section 1 papers (~/Downloads/TSA <year> Section 1.pdf) and answer keys."""
import os, re
import pymupdf
from common import IMG, save_png, write

YEARS = range(2008, 2023)
DL = os.path.expanduser("~/Downloads")
PAGE_OFF = 10000  # y offset per page so a question can run across pages

CT_TYPES = [  # Critical Thinking; anything that matches none of these is Problem Solving
    ("Parallel Reasoning", r"(most )?similar to|parallel|same (\w+ )?(pattern|structure|method)|most closely (parallels|resembles)"),
    ("Flaw", r"flaw|error in (the )?reasoning|questionable|vulnerable to criticism"),
    ("Principle", r"principle|illustrates"),
    ("Assumption", r"assumption|assum(es|ed|ing) (that|which)|rests on|presuppos|depends"),
    ("Weaken", r"weaken|undermine|cast(s)? doubt|challenge|counter"),
    ("Strengthen", r"strengthen|support the (argument|conclusion|claim)|most support"),
    ("Drawing a Conclusion", r"drawn as a conclusion|be (reliably|safely|validly) (concluded|drawn|inferred)|logically completes"),
    ("Main Conclusion", r"main conclusion|best expresses the conclusion|main point|conclusion of the (above )?(argument|passage)\?"),
    ("Drawing a Conclusion", r"(reliably|safely|validly) be (concluded|drawn|inferred)|can (reliably |safely )?be (reliably |safely )?(concluded|drawn|inferred)|can be (concluded|drawn|inferred)|conclusion (can|may) be|follows from|best supported by|must be true|drawn as a conclusion|implication"),
    ("Explanation", r"explain|explanation|account for|resolve"),
]


def shifted(text):
    """Some papers (2012-2014) use fonts whose codes are shifted down by 29 ("7KH" = "The")."""
    return "".join(chr(ord(c) + 29) if ord(c) < 0x62 else c for c in text)


def english_score(t):
    return len(re.findall(r"\b(the|of|and|to|is|in|that|which)\b", t))


def page_lines(page, shift_fonts):
    """Body lines; a leading bold label span ("7", "B") becomes its own line."""
    out = []

    def emit(spans):
        txt = "".join(decode(s, shift_fonts) for s in spans)
        txt = " ".join(txt.split())
        if txt:
            x0 = min(s["bbox"][0] for s in spans if decode(s, shift_fonts).strip())
            out.append({"x0": x0, "y0": min(s["bbox"][1] for s in spans), "x1": max(s["bbox"][2] for s in spans),
                        "y1": max(s["bbox"][3] for s in spans), "text": txt,
                        "bold": all("Bold" in s["font"] for s in spans if decode(s, shift_fonts).strip())})

    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            spans = [s for s in l["spans"]]
            while spans and not decode(spans[0], shift_fonts).strip():
                spans = spans[1:]
            if not spans:
                continue
            first = spans[0]
            t0 = decode(first, shift_fonts).strip()
            if len(spans) > 1 and "Bold" in first["font"] and re.fullmatch(r"[A-E]|\d{1,2}", t0):
                emit([first]); emit(spans[1:])
            else:
                emit(spans)
    return out


def detect_shift(doc):
    fonts = {}
    for p in doc:
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    fonts.setdefault(s["font"], []).append(s["text"])
    return {f for f, ts in fonts.items()
            if english_score(shifted(" ".join(ts))) > 3 * max(1, english_score(" ".join(ts)))}


def decode(span, shift_fonts):
    t = span["text"]
    if not shift_fonts:
        return t
    # label-only fonts carry too little text to detect; their codes give them away
    if span["font"] in shift_fonts or any(ord(c) < 0x20 for c in t) or t.strip() in ("$", "%", "&", "'", "("):
        return shifted(t)
    lower = lambda x: len(re.findall(r"[a-z]", x))
    if lower(shifted(t)) > lower(t):
        return shifted(t)  # e.g. an italic word in another encoded font
    return t


def figure_rects(page):
    rects = []
    for d in page.get_drawings():
        colors = [c for c in (d.get("fill"), d.get("color")) if c]
        if colors and all(min(c) > 0.95 for c in colors):
            continue  # invisible white boxes
        rects.append(d["rect"])
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 1:
            rects.append(pymupdf.Rect(b["bbox"]))
    return rects


def classify(stem):
    s = " ".join(stem.split())
    # data questions ("inferred from these tables") and calculations ("Assuming the same usage...") are
    # Problem Solving even when they use argument words
    if re.match(r"assuming\b", s, re.I) or re.search(r"\b(tables?|graphs?|charts?|results|figures?|data|diagram)\b", s, re.I):
        return "Problem Solving"
    for name, rx in CT_TYPES:
        if re.search(rx, s, re.I):
            return name
    return "Problem Solving"


def load_key(year):
    path = os.path.join(DL, f"TSA {year} Section 1 Answer Key.pdf")
    if year == 2019:
        path = os.path.join(DL, "580266-tsa-oxford-2019-section-1-answer-key-2.pdf")
    if not os.path.exists(path):
        return {}
    text = pymupdf.open(path)[0].get_text()
    text = text.split("score conversion")[0]
    return {int(n): a for n, a in re.findall(r"(?<![\d.])(\d{1,2})\s+([A-E])\b", text) if 1 <= int(n) <= 50}


def paragraphs(lines):
    paras, prev = [], None
    for ln in lines:
        gap = ln["y0"] - prev["y1"] if prev else 0
        if prev is None or gap > 0.6 * (ln["y1"] - ln["y0"]) or (ln["y0"] // PAGE_OFF) != (prev["y0"] // PAGE_OFF):
            paras.append(ln["text"])
        else:
            paras[-1] += " " + ln["text"]
        prev = ln
    return paras


def parse(year):
    doc = pymupdf.open(os.path.join(DL, f"TSA {year} Section 1.pdf"))
    shift = detect_shift(doc)
    stream = []  # every body line, y offset by page
    for pno, page in enumerate(doc):
        h = page.rect.height
        lines = page_lines(page, shift)
        joined = " ".join(l["text"] for l in lines).lower()
        if pno == 0 or re.search(r"blank page|initially designed for print|acknowledgement|permission to reproduce", joined):
            continue  # cover, blank and boilerplate pages
        for ln in lines:
            t = ln["text"]
            w = page.rect.width
            page_no = re.fullmatch(r"\d{1,2}", t) and abs((ln["x0"] + ln["x1"]) / 2 - w / 2) < 40 and (ln["y0"] < 80 or ln["y1"] > h - 80)
            if page_no or ln["y0"] < 30 or ln["y1"] > h - 45 or "UCLES" in t or t.lower() in ("blank page", "[turn over", "turn over") \
                    or re.fullmatch(r"\[?turn over\]?", t, re.I):
                continue
            ln["page"] = pno
            ln["y0"] += pno * PAGE_OFF; ln["y1"] += pno * PAGE_OFF
            stream.append(ln)
    # order by rows (labels and their text can differ by a few points vertically), then left to right
    stream.sort(key=lambda l: (l["y0"] + l["y1"]) / 2)
    rows, ordered = [], []
    for ln in stream:
        yc = (ln["y0"] + ln["y1"]) / 2
        if rows and yc - rows[-1][0] < 4:
            rows[-1][1].append(ln)
        else:
            rows.append((yc, [ln]))
    for _, row in rows:
        ordered += sorted(row, key=lambda l: l["x0"])
    stream = ordered
    # question numbers: bold integers left of the text column, in increasing order
    labels, want, numbers = [], 1, []
    for i, ln in enumerate(stream):
        if ln["bold"] and ln["x0"] < 80 and ln["text"] in (str(want), str(want + 1)):
            labels.append(i); numbers.append(int(ln["text"])); want = int(ln["text"]) + 1
    skipped = sorted(set(range(1, 51)) - set(numbers))
    if skipped:
        print(f"  {year}: question numbers not found: {skipped}")
    key = load_key(year)
    out = []
    for qi, start in enumerate(labels):
        end = labels[qi + 1] if qi + 1 < len(labels) else len(stream)
        region = stream[start + 1:end]
        n = numbers[qi]
        # choice labels: bold single letters A..E, in order
        chl, want = [], "A"
        for j, ln in enumerate(region):
            if ln["bold"] and ln["text"] == want:
                chl.append(j); want = chr(ord(want) + 1)
                if want == "F":
                    break
        head = region[:chl[0]] if chl else region
        choices = []
        for k, j in enumerate(chl):
            lab = region[j]
            stop = chl[k + 1] if k + 1 < len(chl) else len(region)
            parts = [ln["text"] for ln in region[j + 1:stop] if ln["x0"] > lab["x1"] - 1]
            choices.append(" ".join(parts))
        # figures on the pages this question covers
        pages = sorted({ln["page"] for ln in region} | {stream[start]["page"]})
        y_top, y_bot = stream[start]["y0"], (region[-1]["y1"] if region else stream[start]["y1"])
        next_top = stream[labels[qi + 1]]["y0"] if qi + 1 < len(labels) else float("inf")
        fig = []
        for p in pages:
            for r in figure_rects(doc[p]):
                ry0, ry1 = r.y0 + p * PAGE_OFF, r.y1 + p * PAGE_OFF
                if ry1 > y_top - 2 and ry0 < next_top - 2 and ry0 < (p + 1) * PAGE_OFF and r.width * r.height > 30:
                    fig.append((p, r))
                    y_bot = max(y_bot, ry1)  # a figure can extend below the last text line
        paras = paragraphs(head)
        stem = paras[-1] if paras else ""
        item = {
            "id": f"tsa-{year}-{n}",
            "test": "TSA",
            "source": str(year),
            "section": None,
            "type": None,
            "verbal": None,
            "passage": "\n\n".join(paras[:-1]),
            "question": stem,
            "choices": choices,
        }
        missing_choice_text = len(choices) != 5 or any(not c for c in choices)
        if fig or missing_choice_text:
            # render the question block as an image (per page) so diagrams and tables survive
            first_choice_y = region[chl[0]]["y0"] if chl and not missing_choice_text else y_bot + 4
            shots = []
            for p in pages:
                lo = max(y_top, p * PAGE_OFF) - p * PAGE_OFF - 4
                hi = min(first_choice_y - 4, (p + 1) * PAGE_OFF) - p * PAGE_OFF
                hi = min(hi, doc[p].rect.height - 45)
                if hi - lo > 12:
                    shots.append((p, pymupdf.Rect(40, lo, doc[p].rect.width - 30, hi)))
            paths = []
            for k, (p, clip) in enumerate(shots):
                rel = f"img/tsa/{year}-{n}{'' if k == 0 else '-' + str(k + 1)}.png"
                save_png(doc[p].get_pixmap(clip=clip, dpi=130), rel)
                paths.append(rel)
            item["image"] = paths[0] if len(paths) == 1 else paths
            item["passage"] = ""
            item["question"] = stem if not missing_choice_text else "Choose A–E (see the figure)."
            if missing_choice_text:
                item["choices"] = [""] * 5
        qtype = classify(stem)
        item["section"] = "Problem Solving" if qtype == "Problem Solving" else "Critical Thinking"
        item["type"] = qtype
        item["verbal"] = qtype != "Problem Solving"
        if n in key:
            item["answer"] = key[n]
        out.append(item)
    return out


def main():
    os.makedirs(os.path.join(IMG, "tsa"), exist_ok=True)
    allq = []
    for y in YEARS:
        qs = parse(y)
        print(y, "questions", len(qs), "CT", sum(q["verbal"] for q in qs), "PS", sum(not q["verbal"] for q in qs),
              "images", sum("image" in q for q in qs), "answers", sum("answer" in q for q in qs),
              "choice-count!=5", [q["id"].split("-")[-1] for q in qs if len(q["choices"]) != 5])
        allq += qs
    write("tsa", allq)


if __name__ == "__main__":
    main()
