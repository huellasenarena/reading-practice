"""CAT VARC papers saved from 2IIM pages (sources/cat/<year>s<slot>.html)."""
import glob, os, re
from bs4 import BeautifulSoup, NavigableString, Tag
from common import ROOT, LETTERS, write

SRC = os.path.join(ROOT, "sources", "cat")


def text(el):
    """Element text with <br> turned into line breaks (double <br> = paragraph)."""
    out = []
    for node in el.descendants:
        if isinstance(node, NavigableString):
            out.append(str(node))
        elif node.name == "br":
            out.append("\n")
    s = "".join(out)
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
    s = re.sub(r"\n{2,}", "\n\n", s)
    # single <br> separates numbered sentences; keep those as paragraphs too
    s = re.sub(r"\n(?=\s*\d\.\s)", "\n\n", s)
    return s.strip()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


INSTR_RE = re.compile(
    r"^(The passage (below|given below) is (accompanied|followed) by[^.]*\.( Based on the passage, choose the best answer for each question\.)?"
    r"|Read the passage[^.]*\.)\s*", re.I)


def classify(stem, choices, answer, context):
    s = (context + " " + stem).lower()
    if re.search(r"missing in the paragraph|would best fit|best fit the (paragraph|passage)|following sentence would", s):
        return "Sentence Placement"
    if not choices and re.fullmatch(r"\d{4,5}|[A-E]{4,5}", answer or ""):
        return "Para Jumble"
    if not choices and re.fullmatch(r"\d|[A-E]", answer or ""):
        return "Odd Sentence Out"
    if re.search(r"odd sentence|does not fit|doesn.t fit|odd one out", s):
        return "Odd Sentence Out"
    if re.search(r"alternate summaries|essence of the passage|best captures the (essence|gist)", s) or (
            "summar" in s and len(stem) > 400):
        return "Para Summary"
    if re.search(r"(properly sequenced|coherent paragraph|jumbled)", s) and not choices:
        return "Para Jumble"
    return "Reading Comprehension"


def parse(path):
    name = os.path.basename(path)[:-5]
    year, slot = name.split("s")
    soup = BeautifulSoup(open(path).read(), "html.parser")
    main = soup.select_one("div.span_4_of_5") or soup
    out = []
    passage, passage_title, context = None, None, ""
    blocks = []  # (kind, element) in document order
    for el in main.find_all(["h3", "p", "li"]):
        if el.name == "li" and el.parent.name == "ol" and "ques" in (el.parent.get("class") or []):
            blocks.append(("q", el))
        elif el.name in ("p", "h3") and not el.find_parent("li"):
            blocks.append(("t", el))
    for kind, el in blocks:
        if kind == "t":
            t = text(el)
            if el.name == "h3":
                passage_title = re.sub(r"^Passage\s*\d*\s*:\s*", "", " ".join(t.split()))
                continue
            if len(t) > 500:
                passage = INSTR_RE.sub("", t)
                context = ""
            elif t:
                context = t
            continue
        p = el.find("p", recursive=False)
        stem = text(p) if p else ""
        choices = [text(c) for c in el.select("ol.choice > li")]
        tip = el.select_one(".tooltiptext")
        if tip and tip.find("b"):
            tip_b = tip.find("b").get_text(" ", strip=True)
        else:  # newer pages give typed answers without <b>
            tip_b = text(tip).split("\n")[0].strip() if tip else ""
        tip_rest = text(tip).replace(tip_b, "", 1).strip() if tip else ""
        note = None
        if choices and re.search(r"key in", stem, re.I):
            # typed-answer item whose sentences were marked up as a list
            stem += "\n\n" + "\n\n".join(f"{i + 1}. {c}" for i, c in enumerate(choices))
            choices = []
        if choices:
            m = re.match(r"Choice\s+([A-D])", tip_b)
            answer = m.group(1) if m else None
            # the page sometimes gives a letter that does not match the quoted choice text
            if tip_rest:
                hits = [i for i, c in enumerate(choices) if norm(c) and norm(c) == norm(tip_rest)]
                if not hits:
                    hits = [i for i, c in enumerate(choices) if norm(tip_rest)[:60] and norm(c).startswith(norm(tip_rest)[:60])]
                if len(hits) == 1 and LETTERS[hits[0]] != answer:
                    note = (f"Answer key conflict: the source says choice {answer} but quotes the text of "
                            f"choice {LETTERS[hits[0]]}. Using {LETTERS[hits[0]]}.")
                    answer = LETTERS[hits[0]]
        else:
            answer = tip_b.strip()
            m = re.fullmatch(r"Choice\s+([A-E])", answer)
            if m:  # sentences were a lettered list; the answer is the sentence number
                answer = str(LETTERS.index(m.group(1)) + 1)
        qtype = classify(stem, choices, answer, context)
        q = {
            "id": f"cat-{year}-{slot}-{len(out) + 1}",
            "test": "CAT",
            "source": f"{year} Slot {slot}",
            "section": "VARC",
            "type": qtype,
            "verbal": True,
        }
        if qtype == "Reading Comprehension":
            q["passage"] = passage
            q["question"] = stem
        else:
            # verbal-ability items carry their own text; put the instructions above it
            instr = context if context and len(context) < 500 else ""
            q["question"] = (instr + "\n\n" + stem).strip() if instr and instr not in stem else stem
        if choices:
            q["choices"] = choices
        if answer:
            q["answer"] = answer
        if note:
            q["note"] = note
        out.append(q)
    return out


def main():
    qs = []
    for path in sorted(glob.glob(os.path.join(SRC, "*.html"))):
        got = parse(path)
        types = {}
        for q in got:
            types[q["type"]] = types.get(q["type"], 0) + 1
        print(os.path.basename(path), len(got), types, "no-answer:", sum("answer" not in q for q in got),
              "notes:", sum("note" in q for q in got), "rc-no-passage:",
              sum(q["type"] == "Reading Comprehension" and not q.get("passage") for q in got))
        qs += got
    write("cat", qs)


if __name__ == "__main__":
    main()
