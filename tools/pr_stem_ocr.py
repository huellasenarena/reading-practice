"""Second OCR pass for question stems whose first line (the numbered one) the full-page pass missed.

Reads sources/pr/ocr.json, re-reads the top of the question column at 2x, and writes
sources/pr/stem_ocr.json: {page_key: [[text, conf, [x, y, w, h]], ...]} in the same coordinates.
"""
import io, json, os, re
import pymupdf
from ocrmac import ocrmac
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "pr")
ocr = json.load(open(os.path.join(OUT, "ocr.json")))
docs = {"s1": pymupdf.open(os.path.expanduser("~/Desktop/puerto rico.pdf")),
        "rest": pymupdf.open(os.path.expanduser("~/Desktop/rest of pr lsat.pdf"))}
seen, fixes = set(), {}
for k in sorted(ocr, key=lambda k: (k.split("-")[0] != "s1", int(k.split("-")[1]))):
    items = ocr[k]
    qn = next((t for t, c, b in items if re.fullmatch(r"\d+ of \d+", t.strip())), None)
    sec = next((t for t, c, b in items if re.fullmatch(r"Section \d", t.strip())), None)
    if qn is None or (sec, qn) in seen:
        continue
    seen.add((sec, qn))
    right = [t for t, c, b in items if b[0] >= 1200 and 280 <= b[1] < 460]
    if any(re.match(r"\d+\.", t) for t in right):
        continue
    src, i = k.split("-")
    d = docs[src]
    img = Image.open(io.BytesIO(d.extract_image(d[int(i)].get_images()[0][0])["image"]))
    W, H = img.size
    x0, y0 = int(W * 0.15), int(H * 0.26)
    box = (x0 + 1200, y0 + 250, x0 + 2450, y0 + 460)
    crop = img.crop(box)
    big = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    got = []
    for t, c, b in ocrmac.OCR(big, language_preference=["es-ES"], recognition_level="accurate").recognize():
        cw, ch = crop.size
        got.append([t, round(c, 2), [1200 + round(b[0] * cw), 250 + round((1 - b[1] - b[3]) * ch), round(b[2] * cw), round(b[3] * ch)]])
    fixes[k] = got
json.dump(fixes, open(os.path.join(OUT, "stem_ocr.json"), "w"), ensure_ascii=False)
print(len(fixes), "pages re-read:", {k: [g[0][:40] for g in v] for k, v in list(fixes.items())[:6]})
