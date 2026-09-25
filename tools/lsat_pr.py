"""LSAT Puerto Rico PrepTest (Spanish), from LawHub screenshots OCR'd by pr_ocr.py.

Each question is shown over one or more scrolled screenshots; lines from later screenshots are
aligned to the first one using a line of text they share.
"""
import difflib, json, os, re
from common import ROOT, write

OCR = os.path.join(ROOT, "sources", "pr", "ocr.json")
STEM_OCR = os.path.join(ROOT, "sources", "pr", "stem_ocr.json")  # see pr_stem_ocr.py
SPLIT_X = 1200        # passage on the left, question on the right
CHOICE_X = 1400       # choice text is indented further than the stem
GAP = 70              # vertical gap (px) that separates paragraphs / choices
NOISE = {"Directions", "Passage Only View", "Find Text, Type Here", "Prev", "Next", "Reset Response", "a"}

# answer keys read off the LawHub review tables
KEYS = {
    1: "DCDCEEABBDBDDBDDACABEEACEC",
    2: "BEBDABADDCECEBABCDDCDCCDCD",
    3: "ECBEEEAABEEDBCEAAAABDBADD",
    4: "EDBDBCBAEDCCECDACBEAACCABAC",  # from screenshots of the final report
}
SECTION_KIND = {1: "LR", 2: "RC", 3: "LR", 4: "RC"}
# OCR misreads, checked against the screenshots (the other oddities, e.g. "explixaría", are in LawHub's text)
OCR_FIXES = {
    "queivivan": 'que "vivan', "idealesiy": 'ideales" y', "estuerzo": "esfuerzo",
    "imuerte por entropía": '"muerte por entropía', "multimillonarioi": 'multimillonario"',
    "tostatos": "fosfatos", "los panales": "los pañales",
}

LR_TYPES = [  # Spanish question stems
    ("Parallel Flaw", r"(paralel|similar|se asemeja).*(defectuos|error|vulnerable)"),
    ("Parallel Reasoning", r"paralel|más similar|se asemeja más|patrón de razonamiento"),
    ("Flaw", r"vulnerable a la crítica|defecto|error de razonamiento|es cuestionable|razonamiento es defectuoso|falla"),
    ("Principle", r"principio|a tenor con"),
    ("Flaw", r"crítica|falaz|erróneo|defectuoso|no se deriva lógicamente"),
    ("Inference", r"mejor sustentad|tiene que ser ciert|debe ser ciert|debe ser verdader"),
    ("Sufficient Assumption", r"se (infiere|deduce|sigue|desprende) (correctamente|lógicamente|adecuadamente) si|si se supone|si se asume|conclusión .* (se infiere|se sigue) .* si|permite extraer|de asumirse"),
    ("Necessary Assumption", r"presupo|suposici|supuesto|depende de|requiere el argumento|asume"),
    ("Weaken", r"debilita|socava|pone en duda|cuestiona más|contradice|arroja dudas|contrarréplica|objeción"),
    ("Strengthen", r"fortalece|apoya|apoyo|respalda|justifica|sustent"),
    ("Paradox", r"explica|resuelve|reconcilia|discrepancia|aparente"),
    ("Point at Issue", r"desacuerdo|discrepan|comprometid[oa]s? a (estar|coincidir)|coinciden"),
    ("Main Point", r"conclusión (principal|general)|expresa con (más|mayor) precisión la conclusión|conclusión del argumento\?"),
    ("Role", r"papel|función|desempeña|\brol\b"),
    ("Method", r"técnica|estrategia|método|procede|avanza|hace el autor|responde .* (mediante|al)|razonamiento .* (consiste|procede)"),
    ("Evaluate", r"evaluar|útil saber|más útil"),
    ("Must Be False", r"no puede ser ciert|debe ser fals|podría ser ciert[oa] EXCEPTO"),
    ("Inference", r"debe ser ciert|debe ser verdader|apoyan? más firmemente|se puede inferir|se puede concluir|infier|completa|de ser ciertas|si las afirmaciones anteriores"),
]
RC_TYPES = [
    ("Passage Comparison", r"ambos pasajes|pasaje a|pasaje b|los dos pasajes|ambos autores"),
    ("Main Point", r"idea principal|propósito principal|objetivo principal|punto principal|principalmente (interesad|preocupad)|tema central|título|resume"),
    ("Structure", r"organiza|estructura"),
    ("Author's Attitude", r"actitud|tono|estima|valora|aprecia|el autor (estaría|probablemente estaría) de acuerdo|opinión del autor|postura del autor"),
    ("Purpose / Function", r"con el fin de|con el propósito|función|propósito|para (ilustrar|sugerir|mostrar|indicar)|el autor (menciona|se refiere|cita|discute|incluye)"),
    ("Meaning in Context", r"significado|se refiere|significa|el término|la frase|la palabra"),
    ("Strengthen / Weaken", r"fortalece|debilita|socava|apoya|respalda|pone en duda"),
    ("Analogy", r"análog|similar|ilustra|ejemplo"),
    ("Inference", r"mejor sustentad|infier|se desprende"),
    ("Detail", r"según (lo indicado por )?el (pasaje|autor|argumento)|el pasaje (afirma|menciona|indica|establece|dice)|se indica en el pasaje|de acuerdo con el pasaje|información suficiente|según lo indicado|tal como se presenta"),
    ("Analogy", r"a tenor con|escenario"),
    ("Inference", r"infer|infier|sugiere|impli|implí|más probable|estaría de acuerdo|se puede concluir|apoya|compatible|coherente"),
]


def classify(stem, kind):
    s = " ".join(stem.split())
    for name, rx in (LR_TYPES if kind == "LR" else RC_TYPES):
        if re.search(rx, s, re.I):
            return name
    return "Other"


def page_lines(items):
    """(text, x, y) body lines of one screenshot, plus choice-circle letters and the page header."""
    lines, circles, qn, sec = [], [], None, None
    for text, conf, (x, y, w, h) in items:
        t = text.strip()
        m = re.fullmatch(r"(\d+) of (\d+)", t)
        if m:
            qn = int(m.group(1)); continue
        m = re.fullmatch(r"Section (\d)", t)
        if m:
            sec = int(m.group(1)); continue
        if y < 280 or y > 1200 or x > 2000 or t in NOISE or re.search(r"\d+:\d+ / \d+:\d+", t):
            continue
        if re.fullmatch(r"[A-Z]", t) and 1280 < x < 1400:
            circles.append((t, y + h / 2)); continue
        if re.fullmatch(r"[\d\s|\[\]/]+", t):
            continue  # the row of question numbers at the bottom of the screen
        if h <= 20 and conf < 1:
            continue  # the top or bottom sliver of a line cut off by the screen edge ("ЛоИ, цИС")
        m = re.search(r"\s\d{1,2}\.\s", t)
        if x < SPLIT_X < x + w - 100 and m:
            t = t[:m.start()]  # one OCR box ran across both panes into the question number
        for bad, good in OCR_FIXES.items():
            t = t.replace(bad, good)
        # OCR is least reliable at the screen edges, where lines may be cut off
        lines.append({"t": t, "x": x, "y": y, "h": h, "c": conf, "m": min(y - 280, 1200 - (y + h))})
    return qn, sec, lines, circles


def key(t):
    return re.sub(r"\W", "", t.lower())


def merge(pages):
    """Align each screenshot to the previous ones using a shared line of text."""
    merged = []
    for lines in pages:
        lines = sorted(lines, key=lambda l: l["y"])
        if not merged:
            merged = [dict(l) for l in lines]
            continue
        known = {key(l["t"]): l for l in merged if len(l["t"]) > 15}
        # every identical line pair votes for an offset; repeated lines (e.g. two choices that
        # start the same way) are outvoted
        votes = {}
        for a in lines:
            for m in merged:
                if len(a["t"]) > 15 and key(a["t"]) == key(m["t"]):
                    o = round((m["y"] - a["y"]) / 10) * 10
                    votes[o] = votes.get(o, 0) + 1
        if votes:
            best_o = max(votes, key=votes.get)
            pairs = [m["y"] - a["y"] for a in lines for m in merged
                     if len(a["t"]) > 15 and key(a["t"]) == key(m["t"]) and round((m["y"] - a["y"]) / 10) * 10 == best_o]
            off = sum(pairs) / len(pairs)
        else:
            # no identical line: fall back to the most similar pair (OCR differs slightly between shots)
            best = max(((difflib.SequenceMatcher(None, key(a["t"]), k).ratio(), a, m)
                        for a in lines if len(a["t"]) > 15 for k, m in known.items()), default=(0, None, None), key=lambda x: x[0])
            if best[0] >= 0.75:
                off = best[2]["y"] - best[1]["y"]
            else:
                off = max(l["y"] for l in merged) + GAP + 10 - min(l["y"] for l in lines)
        for l in lines:
            l = dict(l, y=l["y"] + off)
            # identical text at the same height is the same line (short lines like "cumplirla." can repeat)
            if any(key(m["t"]) == key(l["t"]) and abs(m["y"] - l["y"]) < 40 for m in merged):
                continue
            # a line cut off at the screen edge in one screenshot shows up whole in the other
            same = next((m for m in merged if abs(m["y"] - l["y"]) < 25 and abs(m["x"] - l["x"]) < 120), None)
            if same:
                if (l["c"], l["m"]) > (same["c"], same["m"]):
                    same.update(t=l["t"], c=l["c"], m=l["m"])
                continue
            merged.append(l)
        merged.sort(key=lambda l: l["y"])
    return merged


def paragraphs(lines):
    paras, prev = [], None
    for l in lines:
        if prev is None or l["y"] - prev["y"] > GAP:
            paras.append(l["t"])
        else:
            paras[-1] = paras[-1] + ("" if paras[-1].endswith("-") else " ") + l["t"]
        prev = l
    return paras


def main():
    ocr = json.load(open(OCR))
    for k, items in json.load(open(STEM_OCR)).items():
        ocr[k] = [it for it in ocr[k] if not (it[2][0] >= 1200 and 250 <= it[2][1] < 460)] + items
    # "extra" screenshots (pr_ocr.py extra) come last, so they extend what the earlier ones show
    order = sorted(ocr, key=lambda k: (["s1", "rest", "extra"].index(k.split("-")[0]), int(k.split("-")[1])))
    groups, sec = {}, 1
    for k in order:
        qn, s, lines, circles = page_lines(ocr[k])
        if qn is None:
            continue  # review tables, instructions
        sec = s or sec
        g = groups.setdefault((sec, qn), {"left": [], "right": [], "circles": []})
        g["left"].append([l for l in lines if l["x"] < SPLIT_X])
        g["right"].append([l for l in lines if l["x"] >= SPLIT_X])
    out, flagged = [], []
    for (sec, qn), g in sorted(groups.items()):
        kind = SECTION_KIND[sec]
        left = merge(g["left"])
        right = merge(g["right"])
        stem_lines = [l for l in right if l["x"] < CHOICE_X]
        choice_lines = [l for l in right if l["x"] >= CHOICE_X]
        stem = " ".join(l["t"] for l in stem_lines)
        stem = re.sub(r"^\d+\.\s*", "", stem)
        choices = paragraphs(choice_lines)
        passage = "\n\n".join(paragraphs(left))
        q = {
            "id": f"lsatpr-{sec}-{qn}",
            "test": "LSAT (Puerto Rico)",
            "source": "Official LSAT – Puerto Rico PrepTest",
            "section": "Logical Reasoning" if kind == "LR" else "Reading Comprehension",
            "type": classify(stem, kind),
            "verbal": True,
            "lang": "es",
            "passage": passage,
            "question": stem,
            "choices": choices,
        }
        if sec in KEYS:
            q["answer"] = KEYS[sec][qn - 1]
        if len(choices) != 5:
            flagged.append((q["id"], len(choices)))
        out.append(q)
    # every question in a Reading Comprehension set gets the most complete copy of its passage
    def shingles(t):
        w = key(t) and re.findall(r"\w+", t.lower())
        return {" ".join(w[i:i + 5]) for i in range(len(w) - 4)}
    rc = [q for q in out if q["section"] == "Reading Comprehension"]
    sh = {q["id"]: shingles(q["passage"]) for q in rc}
    for q in rc:
        mine = sh[q["id"]]
        same = [o for o in rc if o["id"].split("-")[1] == q["id"].split("-")[1] and mine and sh[o["id"]]
                and len(mine & sh[o["id"]]) / min(len(mine), len(sh[o["id"]])) > 0.5]
        q["passage"] = max(same, key=lambda o: len(o["passage"]))["passage"]
    print("questions", len(out), "by section", {s: sum(1 for q in out if q["id"].split("-")[1] == str(s)) for s in (1, 2, 3, 4)})
    print("choice count != 5:", flagged)
    write("lsat_pr", out)


if __name__ == "__main__":
    main()
