"""OCR the answer column of the LawHub review tables (letters are too small for a whole-page pass).

Writes sources/pr/keys_ocr.json: {page_key: [[text, y_in_page_crop_coords], ...]} for the row numbers and letters.
"""
import io, json, os
import pymupdf
from ocrmac import ocrmac
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "pr")
PAGES = [0, 1, 76, 77, 78, 79, 130, 131, 132, 205, 206, 207, 208]
d = pymupdf.open(os.path.expanduser("~/Desktop/rest of pr lsat.pdf"))
res = {}
for i in PAGES:
    img = Image.open(io.BytesIO(d.extract_image(d[i].get_images()[0][0])["image"]))
    W, H = img.size
    x0, y0 = int(W * 0.15), int(H * 0.26)  # same crop origin as pr_ocr.py
    rows = []
    for name, (a, b) in {"num": (320, 390), "ans": (620, 720)}.items():
        strip = img.crop((x0 + a, y0, x0 + b, int(H * 0.96)))
        big = strip.resize((strip.width * 4, strip.height * 4), Image.LANCZOS)
        for t, c, bb in ocrmac.OCR(big, recognition_level="accurate", language_preference=["en-US"]).recognize():
            y = round((1 - bb[1] - bb[3] / 2) * strip.height)
            rows.append([name, t, y])
    res[f"rest-{i}"] = rows
json.dump(res, open(os.path.join(OUT, "keys_ocr.json"), "w"))
print({k: len(v) for k, v in res.items()})
