"""SAT Reading and Writing question bank export (~/Downloads/questionbank-export-*.pdf)."""
import glob, os, re
import pymupdf
from common import IMG, save_png, write

SRC = sorted(glob.glob(os.path.expanduser("~/Downloads/questionbank-export-*.pdf")))[-1]
COLS = [19, 134, 248, 364, 478, 595]  # header table: Assessment, Test, Domain, Skill, Difficulty
BODY_X = 22  # body text starts at x=18; figure labels and choice continuations sit further right


def page_lines(page):
    """Lines as dicts {y0, y1, x0, text} with underlines marked ++like this++.

    The export splits "rt" ligatures with a 0.2pt-wide space ("repor ted"); spaces
    narrower than 1pt are dropped.
    """
    drawings = [d["rect"] for d in page.get_drawings()]
    unders = [r for r in drawings if r.height <= 1.6 and r.width > 3 and r.y0 > 115]
    bullets = [(r.y0 + r.y1) / 2 for r in drawings if r.width < 6 and r.height < 6 and r.x0 < 45]
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            chars = [c for s in l["spans"] for c in s["chars"]]
            text, inside = "", False
            for c in chars:
                x0, y0, x1, y1 = c["bbox"]
                if c["c"] == " " and x1 - x0 < 1.0:
                    continue
                cx = (x0 + x1) / 2
                u = c["c"] != " " and any(r.x0 - 1 <= cx <= r.x1 + 1 and y1 - 4 <= r.y0 <= y1 + 4 for r in unders)
                if u and not inside:
                    text += "++"; inside = True
                elif not u and inside and c["c"] != " ":
                    text = text.rstrip() + "++" + (" " if text.endswith(" ") else ""); inside = False
                text += c["c"]
            if inside:
                text = text.rstrip() + "++"
            text = text.replace("++ ++", " ").strip()
            if text:
                y0, y1 = l["bbox"][1], l["bbox"][3]
                bullet = l["bbox"][0] < 60 and any(y0 <= by <= y1 for by in bullets)
                out.append({"y0": y0, "y1": y1, "x0": l["bbox"][0], "x1": l["bbox"][2], "bullet": bullet,
                            "text": ("• " if bullet else "") + text})
    out.sort(key=lambda r: (round(r["y0"]), r["x0"]))
    merged = []  # glyphs from another font can come out as a separate line at the same height
    for ln in out:
        prev = merged[-1] if merged else None
        if prev and abs(ln["y0"] - prev["y0"]) < 2 and -1 < ln["x0"] - prev["x1"] < 8 and not ln["bullet"]:
            prev["text"] += ln["text"]
            prev["x1"] = ln["x1"]
        else:
            merged.append(ln)
    return merged


def paragraphs(lines):
    """Group consecutive lines into paragraphs using the vertical gap."""
    paras, prev = [], None
    for ln in lines:
        if ln.get("bullet") or (prev is not None and prev.get("in_list") and ln["x0"] < BODY_X):
            paras.append(ln["text"])  # each bullet, and the text after a list, is its own paragraph
            ln["in_list"] = ln.get("bullet")
        elif prev is None or ln["page"] != prev["page"] or ln["y0"] - prev["y1"] > 9:
            if prev is not None and ln["page"] != prev["page"] and paras:
                paras[-1] += " " + ln["text"]  # page break: continue the paragraph
            else:
                paras.append(ln["text"])
        else:
            paras[-1] += " " + ln["text"]
        if not ln.get("bullet"):
            ln["in_list"] = prev.get("in_list", False) and ln["x0"] > BODY_X if prev else False
        prev = ln
    return [p.replace("++ ++", " ") for p in paras]


def norm_label(s):
    s = " ".join(s.split())
    return {"Cross-Text Connections": "Cross-Text Connections", "Cross-text Connections": "Cross-Text Connections"}.get(s, s)


def main():
    doc = pymupdf.open(SRC)
    os.makedirs(os.path.join(IMG, "sat"), exist_ok=True)
    qs, cur = [], None
    for pno, page in enumerate(doc):
        lines = page_lines(page)
        for ln in lines:
            ln["page"] = pno
        start = next((i for i, ln in enumerate(lines) if ln["text"].startswith("Question ID:")), None)
        if start is not None:
            if cur:
                qs.append(cur)
            qid = lines[start]["text"].split(":", 1)[1].strip()
            head = [[] for _ in range(5)]
            for ln in lines:
                if 74 < ln["y0"] < 112:
                    col = next(i for i in range(5) if COLS[i] - 2 <= ln["x0"] < COLS[i + 1])
                    head[col].append(ln["text"])
            cur = {"id": qid, "head": [norm_label(" ".join(h)) for h in head], "q": [], "a": [], "key": None, "r": [],
                   "mode": None, "draw": []}
            body = [ln for ln in lines if ln["y0"] > 115]
        else:
            body = lines
        if cur is None:
            continue
        for ln in body:
            t = ln["text"]
            if t == "Question" and ln["x0"] < BODY_X:
                cur["mode"] = "q"; cur["qpage"] = pno; cur["qy"] = ln["y1"]; continue
            if t == "Answer" and ln["x0"] < BODY_X and cur["mode"] == "q":
                cur["mode"] = "a"; cur["ay"] = ln["y0"]; cur["apage"] = pno; continue
            m = re.fullmatch(r"Correct Answer: ([A-D])", t)
            if m:
                cur["key"] = m.group(1); cur["mode"] = None; continue
            if t == "Rationale" and ln["x0"] < BODY_X:
                cur["mode"] = "r"; continue
            if cur["mode"]:
                cur[cur["mode"]].append(ln)
        # figure drawings inside the question block on this page
        if cur.get("qpage") == pno:
            y_end = cur["ay"] if cur.get("apage") == pno else page.rect.height
            for d in page.get_drawings():
                r = d["rect"]
                if (r.y0 >= cur["qy"] - 1 and r.y1 <= y_end and not (r.height <= 1.6 and r.width > 3)
                        and not (r.width < 6 and r.height < 6)):
                    cur["draw"].append(r)
    qs.append(cur)

    out = []
    for q in qs:
        _, _, domain, skill, diff = q["head"]
        qlines = q["q"]
        image = None
        if q["draw"]:
            fig = pymupdf.Rect(q["draw"][0])
            for r in q["draw"][1:]:
                fig |= r
            # figure titles and axis labels are the lines not flush with the text column
            # (superscripts inside a text row also sit right of the column; skip those)
            rows = [(ln["y0"], ln["y1"]) for ln in qlines if ln["x0"] < BODY_X]
            in_row = lambda ln: any(a - 1 < (ln["y0"] + ln["y1"]) / 2 < b + 1 for a, b in rows)
            for ln in qlines:
                if (ln["x0"] > BODY_X and not in_row(ln)) or fig.contains(pymupdf.Point(ln["x0"] + 1, (ln["y0"] + ln["y1"]) / 2)):
                    fig |= pymupdf.Rect(ln["x0"], ln["y0"], ln["x1"], ln["y1"])
            inside = lambda ln: fig.y0 - 1 <= (ln["y0"] + ln["y1"]) / 2 <= fig.y1 + 1
            qlines = [ln for ln in qlines if not inside(ln)]
            page = doc[q["qpage"]]
            clip = pymupdf.Rect(18, fig.y0 - 6, 594, fig.y1 + 6)
            image = f"img/sat/{q['id']}.png"
            save_png(page.get_pixmap(clip=clip, dpi=144), image)
        paras = paragraphs(qlines)
        stem = paras[-1] if paras else ""
        passage = "\n\n".join(paras[:-1])
        choices = []
        for ln in q["a"]:
            m = re.match(r"([A-D])\.\s*(.*)", ln["text"])
            if m and ln["x0"] < BODY_X and len(choices) == "ABCD".index(m.group(1)):
                choices.append(m.group(2))
            elif choices:
                choices[-1] += " " + ln["text"]
        choices = [c.replace("++ ++", " ") for c in choices]
        item = {
            "id": f"sat-{q['id']}",
            "test": "SAT",
            "source": f"Question bank ({diff})",
            "section": domain,
            "type": skill,
            "verbal": True,
            "passage": passage,
            "question": stem,
            "choices": choices,
            "answer": q["key"],
            "explanation": "\n\n".join(paragraphs(q["r"])),
        }
        if image:
            item["image"] = image
        out.append(item)
    bad = [q["id"] for q in out if len(q["choices"]) != 4 or not q["answer"] or not q["question"]]
    print("questions", len(out), "images", sum("image" in q for q in out),
          "underlined", sum("++" in (q["passage"] + q["question"]) for q in out), "bad", bad[:10], len(bad))
    write("sat", out)


if __name__ == "__main__":
    main()
