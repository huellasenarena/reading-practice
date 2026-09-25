"""Shared helpers for the extraction scripts.

Every question is a dict with these keys (missing ones are omitted):
  id           unique string, e.g. "lsat-140-2-7"
  test         "LSAT", "SAT", "CAT", "TSA", "TAGE MAGE", "LSAT PR"
  source       paper or form, e.g. "PrepTest 140", "2017 Slot 1"
  section      section label within the test, e.g. "Logical Reasoning"
  type         question type used by the type filter
  verbal       false for math / logic / numerical questions (see README)
  passage      text shown on the left (paragraphs separated by blank lines)
  question     the stem
  choices      list of choice strings (absent for typed answers)
  answer       letter "A".. for choice questions, or a string for typed answers
  explanation  text shown after answering
  image        path to an image shown with the passage/question
  lang         "fr" / "es" when not English
  note         warning shown under the question (e.g. doubtful key)
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img")
LETTERS = "ABCDEFGH"


def clean(s):
    """Collapse whitespace inside paragraphs but keep blank-line paragraph breaks."""
    if s is None:
        return None
    s = unicodedata.normalize("NFC", s).replace(" ", " ").replace("\r", "")
    paras = re.split(r"\n\s*\n", s)
    paras = [" ".join(p.split()) for p in paras]
    return "\n\n".join(p for p in paras if p)


def write(name, questions):
    os.makedirs(DATA, exist_ok=True)
    ids = [q["id"] for q in questions]
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"duplicate ids: {sorted(dup)[:5]}"
    for q in questions:
        for k in ("passage", "question", "explanation"):
            if q.get(k):
                q[k] = clean(q[k])
            elif k in q:
                del q[k]
        if "choices" in q:
            q["choices"] = [clean(c) for c in q["choices"]]
    path = os.path.join(DATA, name + ".json")
    with open(path, "w") as f:
        json.dump(questions, f, ensure_ascii=False, separators=(",", ":"))
    _update_index()
    print(f"wrote {path}: {len(questions)} questions")


def _update_index():
    files = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith(".json") and f != "index.json")
    with open(os.path.join(DATA, "index.json"), "w") as f:
        json.dump(files, f)


def save_png(pix, rel_path):
    """Save a PyMuPDF pixmap as a small palette PNG (figures are mostly black and white)."""
    from PIL import Image
    path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.quantize(colors=32, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
