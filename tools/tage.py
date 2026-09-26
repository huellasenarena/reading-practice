"""TAGE MAGE practice booklets (French). Three PDFs with different layouts."""
import os, re
import pymupdf
from common import IMG, mark_hyphen, save_png, write

DL = os.path.expanduser("~/Downloads")
SOURCES = [  # file, id prefix, label shown in the site, data file it goes to
    ("test-tage-mage.pdf", "livret", "Livret du candidat (FNEGE)", "tage"),
    ("TEST-D_ENTRAINEMENT-CORRIGÉ-TAGE-MAGE.pdf", "ecricome", "Test d'entraînement corrigé (Ecricome)", "tage"),
    ("livret_tage_exec.pdf", "exec", "TAGE Executive", "tage"),
    ("livret_tage_exec_n°2.pdf", "exec2", "TAGE Executive n°2", "tage-exec2"),
]
SUBTESTS = {
    1: ("Compréhension de texte", True),
    2: ("Calcul", False),
    3: ("Raisonnement et argumentation", True),
    4: ("Conditions minimales", False),
    5: ("Expression", True),
    6: ("Logique", False),
}
CM_CHOICES = [
    "L'information (1) permet à elle seule de répondre, mais pas l'information (2) seule.",
    "L'information (2) permet à elle seule de répondre, mais pas l'information (1) seule.",
    "Les deux informations ensemble permettent de répondre, mais aucune séparément.",
    "Chaque information permet séparément de répondre.",
    "Les deux informations ensemble ne permettent pas de répondre.",
]
CORRIGE_HEADS = {"COMPRÉHENSION DE TEXTE": 1, "CALCUL": 2, "RAISONNEMENT ET ARGUMENTATION": 3,
                 "CONDITIONS MINIMALES": 4, "EXPRESSION": 5, "LOGIQUE": 6}


def _subtests(**groups):
    return {n: SUBTEST_NUM[name] for name, ns in groups.items() for n in ns}


SUBTEST_NUM = {"comprehension": 1, "calcul": 2, "raisonnement": 3, "cm": 4, "expression": 5, "logique": 6}
# the Executive booklets have no section headings: subtest of each question, read off the booklet
EXEC_SUBTESTS = {
    "exec": _subtests(expression=(1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 22),
                      raisonnement=(6, 8, 12, 41, 52, 54, 56),
                      calcul=(7, 11, 13, 21, 23, 40, 42, 51, 53),
                      logique=(9, 10, 14, 24, 26, 28, 30, 37, 39, 43, 45, 58, 60),
                      cm=(15, 25, 27, 29, 36, 38, 44, 55, 57, 59),
                      comprehension=(31, 32, 33, 34, 35, 46, 47, 48, 49, 50)),
    "exec2": _subtests(expression=(1, 2, 3, 4, 5, 16, 17, 18, 19, 20),
                       raisonnement=(7, 9, 11, 13, 22, 41, 52, 54, 56),
                       calcul=(6, 8, 12, 21, 23, 40, 42, 51, 53),
                       logique=(10, 14, 24, 26, 28, 30, 37, 39, 43, 45, 58, 60),
                       cm=(15, 25, 27, 29, 36, 38, 44, 55, 57, 59),
                       comprehension=(31, 32, 33, 34, 35, 46, 47, 48, 49, 50)),
}
# answer keys that are wrong, checked by hand: (prefix, question) -> (answer, note)
KEY_FIXES = {
    ("exec2", 23): ("C", "The booklet's key says D (43,3), the average of the lap speeds. Over the 3 laps the average "
                         "speed is 3 / (1/30 + 2/50) = 40,9 km/h, which is C."),
}
# reading passages that are not introduced by a "Texte" heading
PASSAGE_STARTS = ("Interview du directeur", "Une réforme du Fonds monétaire",
                  "Ce texte retranscrit la réponse", "C’est un rêve commun")
CHOICE_RE = re.compile(r"(?:^|(?<=\s))([A-E])\s*(?:\)\s*\.?|\.|\s-|\s–)\s*")


def doc_lines(doc):
    out = []
    sizes = sorted(s["size"] for p in doc for b in p.get_text("dict")["blocks"] for l in b.get("lines", [])
                   for s in l["spans"] if s["text"].strip())
    body = sizes[len(sizes) // 2]
    for pno, page in enumerate(doc):
        h = page.rect.height
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                txt = "".join(s["text"] for s in l["spans"])
                txt = re.sub(r" {4,}", " ___ ", txt)  # fill-in blanks are drawn as long runs of spaces
                txt = re.sub(r"(?:_{3}\s*)?\.{4,}(?:\s*_{3})?", "______", txt)  # ...and as dotted lines
                txt = mark_hyphen(" ".join(txt.split()).replace(" ,", ","))  # "Humanisme ," after italics
                if not txt:
                    continue
                x0, y0, x1, y1 = l["bbox"]
                if re.fullmatch(r"(Page )?\d+", txt) and (y0 < 60 or y1 > h - 50):
                    continue
                if "HUB ECRICOME" in txt or "Tous droits réservés" in txt:
                    continue
                txt = re.sub(r"\b1'(?=[A-ZÀ-Ý])", "l'", txt)  # "1'ADN", "1'OMS" in the livret's text layer
                txt = re.sub(r"\bI1\b", "Il", txt)
                bold = any("Bold" in s["font"] for s in l["spans"] if s["text"].strip())
                # exponents and small fractions are set in a smaller size, on their own line fragments
                sup = any(s["size"] < 0.75 * body for s in l["spans"] if s["text"].strip())
                out.append({"page": pno, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": txt, "bold": bold, "sup": sup})
    out.sort(key=lambda l: (l["page"], l["y0"]))
    # a row is lines within 3pt of each other (a fraction can start just above its "Question n." label)
    rows = []
    for ln in out:
        if rows and ln["page"] == rows[-1][0]["page"] and ln["y0"] - rows[-1][0]["y0"] <= 3:
            rows[-1].append(ln)
        else:
            rows.append([ln])
    return _columns([ln for row in rows for ln in sorted(row, key=lambda l: l["x0"])])


def _columns(lines):
    """The livret prints some Logique questions in two columns ("Question 6." and "Question 7." side by side).
    From such a row to the next one, put the left column's lines before the right column's."""
    head = lambda l: l["bold"] and re.match(r"Question\s*\d+", l["text"])
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        pair = [l for l in lines[i:i + 2] if head(l) and l["page"] == ln["page"] and abs(l["y0"] - ln["y0"]) <= 3]
        if len(pair) == 2 and pair[1]["x0"] > 250:
            split = pair[1]["x0"] - 5
            j = i + 2
            while j < len(lines) and lines[j]["page"] == ln["page"] and not (head(lines[j]) and lines[j]["x0"] < split):
                j += 1
            band = lines[i:j]
            left = [dict(l, col=(0, split)) for l in band if l["x0"] < split]
            right = [dict(l, col=(split, None)) for l in band if l["x0"] >= split]
            # each column pair starts a new band, so split the band at the next pair of headings too
            out += _pairwise(left, right, head)
            i = j
        else:
            out.append(ln)
            i += 1
    return out


def _pairwise(left, right, head):
    """Interleave column blocks: left question k, right question k, left question k+1, ..."""
    def blocks(col):
        bl = []
        for l in col:
            if head(l) or not bl:
                bl.append([])
            bl[-1].append(l)
        return bl
    lb, rb = blocks(left), blocks(right)
    out = []
    for k in range(max(len(lb), len(rb))):
        out += (lb[k] if k < len(lb) else []) + (rb[k] if k < len(rb) else [])
    return out


def split_choices(lines):
    """Return (stem_lines, choices, index of the line where choice A starts)."""
    want, choices, stem, first = "A", [], [], None

    def add(seg):
        if seg:
            if choices:
                choices[-1] = (choices[-1] + " " + seg).strip()
            else:
                stem.append(seg)

    for i, ln in enumerate(lines):
        t, pos = ln["text"], 0
        for m in CHOICE_RE.finditer(t):
            if want == "F" or m.group(1) != want:
                continue
            if m.start() > 0 and ")" not in m.group(0):
                continue
            add(t[pos:m.start()].strip())
            choices.append("")
            if first is None:
                first = i
            pos, want = m.end(), chr(ord(want) + 1)
        add(t[pos:].strip())
    return stem, choices, first


def parse_doc(fname, prefix, label):
    doc = pymupdf.open(os.path.join(DL, fname))
    lines = doc_lines(doc)
    blocks, sub, passage, pend, cur, consignes = [], None, None, [], None, {}
    for i, ln in enumerate(lines):
        t = ln["text"]
        if re.fullmatch(r"CORRIGÉ", t) or re.match(r"Réponses\s*:", t) or (t == "QUESTIONS" and ln["bold"]):
            break
        m = re.match(r"(?:Sous-test|SOUS-TEST)\s*(\d)", t)
        if m and (ln["bold"] or t.startswith("SOUS-TEST")) and "_" not in t:  # not the table of contents
            if cur: blocks.append(cur); cur = None
            sub, passage, pend = int(m.group(1)), None, []
            continue
        if ln["page"] == 0:
            continue
        m = re.match(r"Consigne de (\d+) à (\d+)\s*:\s*(.*)", t)
        mq = re.match(r"Questions (\d+) à (\d+)\s*:\s*(.*)", t)
        if m or mq:
            mm = m or mq
            if cur: blocks.append(cur); cur = None
            text = mm.group(3)
            j = i + 1
            while j < len(lines) and lines[j]["bold"] and not lines[j]["text"].startswith("Question"):
                text += " " + lines[j]["text"]; j += 1
            for n in range(int(mm.group(1)), int(mm.group(2)) + 1):
                consignes[(sub, n)] = text
            pend = []
            continue
        if (re.match(r"Texte\b", t) and ln["bold"]) or re.match(r"Texte\.?\s*(\d+|[IVX]+)\b", t) \
                or t.startswith(PASSAGE_STARTS):
            if cur: blocks.append(cur); cur = None
            pend = [ln]
            continue
        m = re.match(r"Question\s*(\d+)\s*[.:]?\s*(.*)", t)
        if m and ln["bold"]:
            if cur: blocks.append(cur)
            # text between the previous question and this one: a passage or instructions
            ptxt = " ".join(p["text"] for p in pend)
            if len(ptxt) > 400:
                passage = pend[:]
            pend = []
            cur = {"sub": sub, "n": int(m.group(1)), "lines": [], "top": ln, "passage": passage}
            if m.group(2):
                cur["lines"].append(dict(ln, text=m.group(2)))
            continue
        if cur is not None:
            # after choice E, anything not indented like a continuation belongs to what comes next
            _, ch, _ = split_choices(cur["lines"])
            # (a line ending in "et", "de", a comma... is unfinished, even if the next one starts with a capital)
            unfinished = re.search(r"(,|\b(et|ou|de|du|des|à|au|aux|la|le|les|un|une|en|que|qui|pour|par|sur|dans|avec))$",
                                   cur["lines"][-1]["text"])
            if len(ch) == 5 and not (ln["x0"] > cur["lines"][-1]["x0"] + 5 or re.match(r"[a-zà-ü(]", t) or unfinished) \
                    and cur["sub"] != 4:
                blocks.append(cur); cur = None
                pend = [ln]
                continue
            cur["lines"].append(ln)
        else:
            pend.append(ln)
    if cur:
        blocks.append(cur)
    return doc, lines, blocks, consignes


def answer_keys(doc, lines, prefix):
    """{(subtest, n): letter} and {(subtest, n): explanation}."""
    keys, expl = {}, {}
    text = "\n".join(p.get_text() for p in doc)
    if prefix == "livret":
        tail = text[text.rfind("Sous-test 1 : Compréhension"):]
        parts = re.split(r"Sous-test (\d)\s*:", tail)
        for k in range(1, len(parts), 2):
            sub, body = int(parts[k]), parts[k + 1]
            nums = [int(x) for grp in re.findall(r"QUESTIONS\s+([\d\s]+?)\s*REPONSES", body) for x in grp.split()]
            lets = [x for grp in re.findall(r"REPONSES\s+([A-E/\s]+?)(?=\s*(?:\d+\s+)?(?:QUESTIONS|NOTATION|Sous-test)|\s*$)", body) for x in grp.split()]
            for n, a in zip(nums, lets):
                if a != "/":  # "/" = no answer given
                    keys[(sub, n)] = a
    elif prefix == "ecricome":
        start = text.find("CORRIGÉ")
        body = text[start:]
        heads = [(m.start(), CORRIGE_HEADS[m.group(1)]) for m in
                 re.finditer(r"^(" + "|".join(CORRIGE_HEADS) + r")\s*$", body, re.M)]
        for k, (pos, sub) in enumerate(heads):
            seg = body[pos:heads[k + 1][0] if k + 1 < len(heads) else len(body)]
            grid = re.search(r"Réponse\s+((?:[A-E]\s+){14}[A-E])", seg)
            if grid:
                for n, a in enumerate(grid.group(1).split(), 1):
                    keys[(sub, n)] = a
            for m in re.finditer(r"Corrigé\s*(\d+)\.\s*Réponse\s*([A-E])\s*(.*?)(?=Corrigé\s*\d+\.\s*Réponse|\Z)", seg, re.S):
                ex = re.sub(r"Page \d+\s*|HUB ECRICOME.*?réservés", "", m.group(3))
                ex = re.sub(r"\s*\n\s*", " ", ex).strip()
                expl[(sub, int(m.group(1)))] = ex
    else:
        body = text[text.find("Réponses"):]
        for n, a in re.findall(r"(\d+)\s+([A-E])\b", body):
            keys[("exec", int(n))] = a
    return keys, expl


def crop(doc, block, next_top, stop_line, rel):
    """Render a question block as one image per page."""
    top = block["top"]
    lines = [block["top"]] + block["lines"]
    cx0, cx1 = top.get("col") or (None, None)  # column bounds for two-column pages
    end_page = lines[-1]["page"] if stop_line is None else stop_line["page"]
    paths = []
    for p in range(top["page"], end_page + 1):
        page = doc[p]
        # start just above the question's first row (a fraction there can sit higher than the label)
        row = [l["y0"] for l in lines if l["page"] == p and abs(l["y0"] - top["y0"]) <= 3]
        y0 = min(row) - 1.5 if p == top["page"] else 50
        on_page = [l for l in lines if l["page"] == p]
        y1 = max([l["y1"] for l in on_page] + [y0 + 10])
        if stop_line is not None and stop_line["page"] == p:
            y1 = stop_line["y0"] - 3
        # drawings and pictures below the last text line (grids, figures)
        limit = next_top["y0"] - 4 if next_top and next_top["page"] == p else page.rect.height - 60
        if stop_line is None or stop_line["page"] != p:
            for r in [d["rect"] for d in page.get_drawings()] + [pymupdf.Rect(b["bbox"]) for b in
                                                                  page.get_text("dict")["blocks"] if b["type"] == 1]:
                in_col = (cx0 is None or r.x0 >= cx0 - 5) and (cx1 is None or r.x1 <= cx1 + 5)
                if r.y0 >= y0 and r.y1 <= limit and r.width * r.height > 20 and in_col:
                    y1 = max(y1, r.y1 + 3)
        if y1 - y0 < 8:
            continue
        clip = pymupdf.Rect(max(30, cx0 or 0), y0, cx1 or page.rect.width - 25, y1 + 2)
        path = rel if not paths else rel.replace(".png", f"-{len(paths) + 1}.png")
        # annots=False leaves out a previous owner's ink answer marks and highlights
        save_png(page.get_pixmap(clip=clip, dpi=130, annots=False), path)
        paths.append(path)
    return paths[0] if len(paths) == 1 else paths


def is_math(line, margin):
    """Exponent-sized text, or a fragment of a stacked fraction ("+", "b", "2") set off from the margin."""
    return line["sup"] or (len(line["text"]) <= 3 and line["x0"] > margin + 20)


def stem_lines_src(block, first):
    return block["lines"][:first] if first is not None else block["lines"]


def main():
    os.makedirs(os.path.join(IMG, "tage"), exist_ok=True)
    for name in dict.fromkeys(s[3] for s in SOURCES):
        group = [s[:3] for s in SOURCES if s[3] == name]
        missing = [f for f, _, _ in group if not os.path.exists(os.path.join(DL, f))]
        if missing:  # the originals are not committed: leave that data file as it is
            print(f"skipped data/{name}.json, PDF not found: {', '.join(missing)}")
            continue
        write(name, build(group))


def build(sources):
    out = []
    for fname, prefix, label in sources:
        doc, lines, blocks, consignes = parse_doc(fname, prefix, label)
        keys, expl = answer_keys(doc, lines, prefix)
        # the livret has two sets of Compréhension questions (1-15 and 16-30) etc.; keep numbers as printed
        for bi, b in enumerate(blocks):
            n = b["n"]
            sub = b["sub"]
            consigne = consignes.get((sub, n))
            if prefix in EXEC_SUBTESTS:
                consigne = next((v for (s, k), v in consignes.items() if k == n), None)
                sub = EXEC_SUBTESTS[prefix][n]
            name, verbal = SUBTESTS[sub]
            stem_lines, choices, first = split_choices(b["lines"])
            stem = " ".join(l for l in stem_lines)
            stem = re.sub(r"\s*Vous devez décider si les informations.*", "", stem)
            stem = re.sub(r"\s+(?=\d\)\s)", "\n\n", stem)  # numbered statements on their own lines
            q = {
                "id": f"tage-{prefix}-{sub}-{n}" if prefix not in EXEC_SUBTESTS else f"tage-{prefix}-{n}",
                "test": "TAGE MAGE",
                "source": label,
                "section": name,
                "type": name,
                "verbal": verbal,
                "lang": "fr",
            }
            if b.get("passage") and sub == 1:
                q["passage"] = "\n\n".join(_paragraphs(b["passage"]))
            if consigne:
                stem = consigne.strip() + "\n\n" + stem
            q["question"] = stem
            if sub == 4:
                q["choices"] = CM_CHOICES
            elif len(choices) == 5:
                q["choices"] = [c.strip(" _") for c in choices]
            else:
                q["choices"] = [""] * 5
            # fractions and exponents in the choices do not survive as text: keep them in the image instead
            margin = min([l["x0"] for l in b["lines"]] or [0])
            tail = b["lines"][first:] if first is not None else []
            labelled = [l for l in tail if CHOICE_RE.match(l["text"])]
            # a formula piece (e.g. a denominator) printed on the same row as the choices
            stray = any(not CHOICE_RE.match(l["text"]) and any(abs(l["y0"] - o["y0"]) <= 3 for o in labelled)
                        for l in tail)
            math = sub != 4 and not verbal and len(choices) == 5 and (
                len(set(choices)) < 5 or stray or any(is_math(l, margin) for l in tail))
            if math:
                q["choices"] = [""] * 5
            # same for a Conditions minimales stem with a formula: the image already shows it
            if sub == 4 and any(is_math(l, margin) for l in stem_lines_src(b, first)):
                q["question"] = consigne or ""
            if not verbal or len(choices) != 5 and sub != 4:
                side = lambda blk: bool(blk["top"].get("col") and blk["top"]["col"][0] > 0)
                nxt = next((o["top"] for o in blocks[bi + 1:] if side(o) == side(b)), None)
                if nxt is None:  # last question: stop at whatever follows it (the livret's answer grid)
                    last = (b["lines"] or [b["top"]])[-1]
                    k = next(k for k, l in enumerate(lines) if l is last)
                    nxt = lines[k + 1] if k + 1 < len(lines) else None
                stop = b["lines"][first] if (first is not None and len(choices) == 5 and sub != 4 and not math) else None
                # choice A on the same row as the end of the stem: keep the whole block
                if stop and any(l["page"] == stop["page"] and l["y1"] > stop["y0"] + 2 for l in b["lines"][:first]):
                    stop = None
                q["image"] = crop(doc, b, nxt, stop, f"img/tage/{prefix}-{sub}-{n}.png")
                if sub != 4:
                    q["question"] = consigne or ""
            key = keys.get(("exec", n)) if prefix in EXEC_SUBTESTS else keys.get((b["sub"], n))
            if (prefix, n) in KEY_FIXES:
                key, q["note"] = KEY_FIXES[(prefix, n)]
            if key:
                q["answer"] = key
            if expl.get((b["sub"], n)):
                q["explanation"] = expl[(b["sub"], n)]
            out.append(q)
        subs = {}
        for q in out:
            if q["source"] == label:
                subs[q["section"]] = subs.get(q["section"], 0) + 1
        print(label, len([q for q in out if q["source"] == label]), subs,
              "no-answer", sum(1 for q in out if q["source"] == label and "answer" not in q),
              "expl", sum(1 for q in out if q["source"] == label and "explanation" in q))
    return out


def _paragraphs(lines):
    # justified text with no space between paragraphs (Executive n°2): a sentence that ends on a short line ends
    # the paragraph. Only when most lines reach the right margin, so ragged-right text is not split.
    right = max(l["x1"] for l in lines)
    justified = sum(l["x1"] > right - 3 for l in lines) > len(lines) / 2
    short_end = lambda l: justified and l["x1"] < right - 30 and re.search(r"[.!?:»…]$", l["text"])
    paras, prev = [], None
    for ln in lines:
        if prev is None or (ln["page"] == prev["page"] and ln["y0"] - prev["y1"] > 6) or ln["bold"] != prev["bold"] \
                or short_end(prev):
            paras.append(ln["text"])
        else:
            paras[-1] += " " + ln["text"]
        prev = ln
    return paras


if __name__ == "__main__":
    main()
