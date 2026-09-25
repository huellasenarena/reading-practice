"""LSAT PrepTests printed from LSAT Warthog (~/Desktop/lsat *.pdf)."""
import os, re
import pymupdf
from common import write

FILES = {  # file -> PrepTest number printed on its title page
    "lsat 140.pdf": None, "lsat 141.pdf": None, "lsat 151.pdf": None, "lsat 158.pdf": None,
}
SECTION = {"LR": "Logical Reasoning", "RC": "Reading Comprehension"}

LR_TYPES = [  # first match wins
    ("Parallel Flaw", r"(parallel|most similar|closely parallels).*(flaw|question|error)|(flaw|question).*(parallel|most similar)"),
    ("Parallel Reasoning", r"parallel|most similar (in its|to)|pattern of reasoning|most closely conforms? to the pattern"),
    ("Point at Issue", r"disagree|point at issue|committed to (agreeing|disagreeing)|agree about|agree that"),
    ("Flaw", r"flaw|vulnerable to (the )?(criticism|objection)|subject to criticism|misleading|questionable aspect|questionable because|error(s)? (of|in) reasoning|reasoning is (most )?questionable|criticized on the grounds"),
    ("Principle", r"principle|best illustrates which|conforms to which|illustrates which one of the following (propositions|generalizations)"),
    ("Sufficient Assumption", r"(follows logically|properly drawn|properly inferred) if|enables? the (argument's )?conclusion|if which one of the following is assumed|conclusion (of the argument )?follows logically if"),
    ("Necessary Assumption", r"assum|presuppos|depends on|relies on"),
    ("Weaken", r"weaken|alternative explanation|undermine|cast(s)? (the most )?doubt|call(s)? into question|counter|damage|challenge"),
    ("Strengthen", r"strengthen|most (strongly )?support(s)? the (argument|conclusion|claim|position|prediction|hypothesis|reasoning|scientist|argument's)|provides? the most support for|add the most support|supports? the \w+'s (reasoning|argument)|justif"),
    ("Paradox", r"resolve|explain|explanation|reconcile|discrepancy|paradox|apparent conflict"),
    ("Main Point", r"main (point|conclusion)|overall conclusion|most accurately expresses the conclusion|conclusion (drawn )?(in|of) the argument\?|expresses the conclusion"),
    ("Role", r"role|figures? in the argument|function(s)? in the"),
    ("Method", r"proceeds by|technique|strategy|method of|responds to .* by|argues by|by doing which|reasoning (in the argument )?(proceeds|does which)|describes how"),
    ("Evaluate", r"evaluat|useful to (know|determine)|most helpful to (know|determine)|most relevant"),
    ("Must Be False", r"cannot be true|must be false|could be true EXCEPT|inconsistent with"),
    ("Inference", r"must (also )?be true|most strongly supported|properly (be )?inferred|can be concluded|could (properly|reasonably) be concluded|follows logically from|most strongly support|most supported|logically completes|infer|most (likely|reasonably) (to )?be|completes? the (passage|argument)"),
]

RC_TYPES = [
    ("Passage Comparison", r"both passages|both of the passages|two passages|passage a and passage b|the authors of both"),
    ("Main Point", r"main (point|idea|purpose)|primarily concerned|primary purpose of the passage|central (idea|point|thesis|topic)|best (describes|expresses) the main|summary of the passage|title"),
    ("Structure", r"organization|structure of the passage|organized|sequence of|which one of the following best describes the (organization|structure)"),
    ("Author's Attitude", r"attitude|tone|author's (view|position|stance)|author would be most likely to (agree|describe)|author regards|author views|would the author"),
    ("Purpose / Function", r"in order to|primarily (to|in order)|function|serves? (to|which one of the following purposes)|purpose|mentions? .* (to|in order)|author (discusses|refers|cites|uses|includes|introduces)|most likely (discusses|mentions|refers)"),
    ("Meaning in Context", r"meaning of|refers to|most nearly means|used to mean|the word|the phrase|the term"),
    ("Strengthen / Weaken", r"strengthen|weaken|undermine|support the|cast(s)? doubt|challenge"),
    ("Analogy", r"analogous|most similar|most like|parallel|illustrates|exemplif|example of"),
    ("Passage Comparison", r"passage a|passage b"),
    ("Detail", r"according to the passage|the passage (states|mentions|indicates|asserts|says)|the author (states|mentions|asserts)|explicitly|identified as|information in the passage|does the passage say|according to the author|information sufficient to answer|as presented in the passage"),
    ("Strengthen / Weaken", r"help to explain|most help"),
    ("Inference", r"infer|suggest|impl|most (likely|strongly)|would agree|would most likely|can be concluded|supported by the passage|compatible|consistent|logically complete"),
]


def classify(stem, section):
    s = " ".join(stem.split())
    table = LR_TYPES if section == "LR" else RC_TYPES
    for name, rx in table:
        if re.search(rx, s, re.I):
            return name
    return "Other"


def lines_of(doc, start, end):
    """Yield (text, x0, font, size, italic) for body lines on pages [start, end)."""
    for i in range(start, end):
        for b in doc[i].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                spans = l["spans"]
                if not spans or spans[0]["size"] < 8:  # printer header/footer
                    continue
                if l["bbox"][1] >= 720:  # clipped copy of a line that is repeated on the next page
                    continue
                txt = ""
                for sp in spans:
                    t = sp["text"]
                    if "Italic" in sp["font"] and t.strip():
                        t = f"*{t}*" if not t.startswith(" ") else f" *{t.strip()}* "
                    txt += t
                txt = txt.replace("* *", " ").strip()
                if txt:
                    yield txt, l["bbox"][0], spans[0]["font"], round(spans[0]["size"], 1)


def join_lines(parts):
    """Join wrapped lines; "\n\n" entries mark paragraph breaks."""
    out = ""
    for p in parts:
        if p == "\n\n":
            out = out.rstrip() + "\n\n"
        elif out and not out.endswith("\n\n"):
            # lines broken after a hyphen or dash join without a space
            out += p if out.endswith(("-", "—", "/")) and not out.endswith(" -") else " " + p
        else:
            out += p
    # descenders (g j p q y) of a line clipped at a page edge survive as junk tokens
    out = re.sub(r"(?:(?<=\s)[gjpqy()\[\]]{1,2}\s+){3,}", "", out)
    return out.strip()


def parse(path):
    doc = pymupdf.open(path)
    title = doc[0].get_text()
    pt = re.search(r"PrepTest (\d+)", title).group(1)
    key_page = next(i for i in range(len(doc)) if "Answer Key" in doc[i].get_text() and
                    re.search(r"Q1: \([A-E]\)", doc[i].get_text() + (doc[i + 1].get_text() if i + 1 < len(doc) else "")))
    expl_page = next(i for i in range(key_page, len(doc)) if "Detailed Explanations" in doc[i].get_text())

    questions, sec_code, sec_no, cur, mode = [], None, 0, None, None

    def flush():
        if cur:
            questions.append(cur)

    for txt, x0, font, size in lines_of(doc, 0, key_page + 1):
        m = re.match(r"Section (\d): (LR|RC)", txt)
        if m and size > 13:
            flush(); cur = None
            sec_no, sec_code, mode = int(m.group(1)), m.group(2), "dir"
            continue
        if txt == "Answer Key":
            break
        m = re.fullmatch(r"Question (\d+)", txt)
        if m and "SFNS" in font:
            flush()
            cur = {"sec": sec_no, "code": sec_code, "n": int(m.group(1)), "pass": [], "stem": [], "ch": []}
            mode = "pass"
            continue
        if cur is None or mode == "dir":
            continue
        if re.fullmatch(r"\([A-E]\)", txt) and "Bold" in font:
            cur["ch"].append([]); mode = "ch"
            continue
        if size >= 12 and "Bold" in font:
            cur["stem"].append(txt); mode = "stem"
            continue
        if mode == "pass":
            if x0 > 70 and cur["pass"]:  # indented first line = new paragraph
                cur["pass"].append("\n\n")
            cur["pass"].append(txt)
        elif mode == "ch":
            cur["ch"][-1].append(txt)
        elif mode == "stem":  # regular text after a stem but before choices (e.g. roman-numeral lists)
            cur["stem"].append(txt)
    flush()

    # answer key: sections in order, "Qn: (X)"
    key_text = "\n".join(doc[i].get_text() for i in range(key_page, expl_page + 1))
    key_text = key_text.split("Answer Key", 1)[1].split("Detailed Explanations")[0]
    keys, sec = [], -1
    for n, a in re.findall(r"Q(\d+): \(([A-E])\)", key_text):
        if n == "1":
            keys.append({}); sec += 1
        keys[sec][int(n)] = a

    # explanations, in section order, restarting at Question 1
    expl, sec, curq, buf = [], -1, None, []
    def eflush():
        if curq is not None:
            expl[sec][curq] = buf[:]
    for txt, x0, font, size in lines_of(doc, expl_page, len(doc)):
        m = re.match(r"Question (\d+) - Correct Answer: \(([A-E])\)", txt)
        if m:
            eflush(); buf = []
            curq = int(m.group(1))
            if curq == 1 or sec < 0 or curq in expl[sec]:
                expl.append({}); sec += 1
            continue
        if curq is None:
            continue
        m = re.match(r"\(([A-E])\)\s*([✓✗])\s*(.*)", txt)
        if m:
            buf.append("\n\n"); buf.append(f"**({m.group(1)}) {'Correct' if m.group(2) == '✓' else 'Incorrect'}.**")
            continue
        buf.append(txt)
    eflush()

    sections = sorted({q["sec"] for q in questions})
    out = []
    for q in questions:
        si = sections.index(q["sec"])
        answer = keys[si].get(q["n"]) if si < len(keys) else None
        ex = expl[si].get(q["n"]) if si < len(expl) else None
        stem = join_lines(q["stem"])
        item = {
            "id": f"lsat-{pt}-{q['sec']}-{q['n']}",
            "test": "LSAT",
            "source": f"PrepTest {pt}",
            "section": SECTION[q["code"]],
            "type": classify(stem, q["code"]),
            "verbal": True,
            "passage": join_lines(q["pass"]),
            "question": stem,
            "choices": [join_lines(c) for c in q["ch"]],
        }
        if answer:
            item["answer"] = answer
        if ex:
            item["explanation"] = join_lines(ex)
        out.append(item)
    return pt, out, len(keys), len(expl)


def main():
    allq = []
    for f in FILES:
        pt, qs, nk, ne = parse(os.path.expanduser("~/Desktop/" + f))
        by = {}
        for q in qs:
            by.setdefault(q["id"].rsplit("-", 1)[0], []).append(q)
        print(f, "-> PT", pt, {k: len(v) for k, v in by.items()}, "keysecs", nk, "explsecs", ne,
              "bad-choices", sum(len(q["choices"]) != 5 for q in qs), "no-ans", sum("answer" not in q for q in qs),
              "no-expl", sum("explanation" not in q for q in qs))
        allq += qs
    write("lsat", allq)


if __name__ == "__main__":
    main()
