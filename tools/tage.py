"""TAGE MAGE practice booklets (French). Three PDFs with different layouts."""
import os, re
import pymupdf
from common import IMG, save_png, write

DL = os.path.expanduser("~/Downloads")
SOURCES = [  # file, id prefix, label shown in the site
    ("test-tage-mage.pdf", "livret", "Livret du candidat (FNEGE)"),
    ("TEST-D_ENTRAINEMENT-CORRIGÉ-TAGE-MAGE.pdf", "ecricome", "Test d'entraînement corrigé (Ecricome)"),
    ("livret_tage_exec.pdf", "exec", "TAGE Executive"),
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
# the Executive booklet has no section headings: subtest of each question, read off the booklet
EXEC_SUBTESTS = {n: 5 for n in (1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 22)}
EXEC_SUBTESTS.update({n: 3 for n in (6, 8, 12, 41, 52, 54, 56)})
EXEC_SUBTESTS.update({n: 2 for n in (7, 11, 13, 21, 23, 40, 42, 51, 53)})
EXEC_SUBTESTS.update({n: 6 for n in (9, 10, 14, 24, 26, 28, 30, 37, 39, 43, 45, 58, 60)})
EXEC_SUBTESTS.update({n: 4 for n in (15, 25, 27, 29, 36, 38, 44, 55, 57, 59)})
EXEC_SUBTESTS.update({n: 1 for n in (31, 32, 33, 34, 35, 46, 47, 48, 49, 50)})
# reading passages that are not introduced by a "Texte" heading
PASSAGE_STARTS = ("Interview du directeur", "Une réforme du Fonds monétaire")
CHOICE_RE = re.compile(r"(?:^|(?<=\s))([A-E])\s*(?:\)\s*\.?|\.|\s-|\s–)\s*")


def doc_lines(doc):
    out = []
    for pno, page in enumerate(doc):
        h = page.rect.height
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                txt = "".join(s["text"] for s in l["spans"])
                txt = re.sub(r" {4,}", " ___ ", txt)  # fill-in blanks are drawn as long runs of spaces
                txt = re.sub(r"(?:_{3}\s*)?\.{4,}(?:\s*_{3})?", "______", txt)  # ...and as dotted lines
                txt = " ".join(txt.split())
                if not txt:
                    continue
                x0, y0, x1, y1 = l["bbox"]
                if re.fullmatch(r"(Page )?\d+", txt) and (y0 < 60 or y1 > h - 50):
                    continue
                if "HUB ECRICOME" in txt or "Tous droits réservés" in txt:
                    continue
                bold = any("Bold" in s["font"] for s in l["spans"] if s["text"].strip())
                out.append({"page": pno, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": txt, "bold": bold})
    out.sort(key=lambda l: (l["page"], round(l["y0"]), l["x0"]))
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
            if len(ch) == 5 and not (ln["x0"] > cur["lines"][-1]["x0"] + 5 or re.match(r"[a-zà-ü(]", t)) \
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
    end_page = lines[-1]["page"] if stop_line is None else stop_line["page"]
    paths = []
    for p in range(top["page"], end_page + 1):
        page = doc[p]
        y0 = top["y0"] - 4 if p == top["page"] else 50
        on_page = [l for l in lines if l["page"] == p]
        y1 = max([l["y1"] for l in on_page] + [y0 + 10])
        if stop_line is not None and stop_line["page"] == p:
            y1 = stop_line["y0"] - 3
        # drawings and pictures below the last text line (grids, figures)
        limit = next_top["y0"] - 4 if next_top and next_top["page"] == p else page.rect.height - 60
        if stop_line is None or stop_line["page"] != p:
            for r in [d["rect"] for d in page.get_drawings()] + [pymupdf.Rect(b["bbox"]) for b in
                                                                  page.get_text("dict")["blocks"] if b["type"] == 1]:
                if r.y0 >= y0 and r.y1 <= limit and r.width * r.height > 20:
                    y1 = max(y1, r.y1 + 3)
        if y1 - y0 < 8:
            continue
        clip = pymupdf.Rect(30, y0, page.rect.width - 25, y1 + 2)
        path = rel if not paths else rel.replace(".png", f"-{len(paths) + 1}.png")
        save_png(page.get_pixmap(clip=clip, dpi=130), path)
        paths.append(path)
    return paths[0] if len(paths) == 1 else paths


def main():
    os.makedirs(os.path.join(IMG, "tage"), exist_ok=True)
    out = []
    for fname, prefix, label in SOURCES:
        doc, lines, blocks, consignes = parse_doc(fname, prefix, label)
        keys, expl = answer_keys(doc, lines, prefix)
        # the livret has two sets of Compréhension questions (1-15 and 16-30) etc.; keep numbers as printed
        for bi, b in enumerate(blocks):
            n = b["n"]
            sub = b["sub"]
            consigne = consignes.get((sub, n))
            if prefix == "exec":
                consigne = next((v for (s, k), v in consignes.items() if k == n), None)
                sub = EXEC_SUBTESTS[n]
            name, verbal = SUBTESTS[sub]
            stem_lines, choices, first = split_choices(b["lines"])
            stem = " ".join(l for l in stem_lines)
            stem = re.sub(r"\s*Vous devez décider si les informations.*", "", stem)
            stem = re.sub(r"\s+(?=\d\)\s)", "\n\n", stem)  # numbered statements on their own lines
            q = {
                "id": f"tage-{prefix}-{sub}-{n}" if prefix != "exec" else f"tage-exec-{n}",
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
            if not verbal or len(choices) != 5 and sub != 4:
                nxt = blocks[bi + 1]["top"] if bi + 1 < len(blocks) else None
                stop = b["lines"][first] if (first is not None and len(choices) == 5 and sub != 4) else None
                q["image"] = crop(doc, b, nxt, stop, f"img/tage/{prefix}-{sub}-{n}.png")
                if sub != 4:
                    q["question"] = consigne or ""
            key = keys.get(("exec", n)) if prefix == "exec" else keys.get((b["sub"], n))
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
    write("tage", out)


def _paragraphs(lines):
    paras, prev = [], None
    for ln in lines:
        if prev is None or (ln["page"] == prev["page"] and ln["y0"] - prev["y1"] > 6) or ln["bold"] != prev["bold"]:
            paras.append(ln["text"])
        else:
            paras[-1] += " " + ln["text"]
        prev = ln
    return paras


if __name__ == "__main__":
    main()
