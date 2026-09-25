"""OCR the Puerto Rico LSAT screenshots (LawHub) with the macOS Vision framework -> sources/pr/ocr.json."""
import pymupdf, os, sys, json, io
from ocrmac import ocrmac
from PIL import Image
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "pr")
out = {}
for key, f in (("s1", "~/Desktop/puerto rico.pdf"), ("rest", "~/Desktop/rest of pr lsat.pdf")):
    d = pymupdf.open(os.path.expanduser(f))
    pages = range(len(d)) if len(sys.argv) < 2 else [int(x) for x in sys.argv[1].split(",")]
    for i in pages:
        if i >= len(d): continue
        xref = d[i].get_images()[0][0]
        img = Image.open(io.BytesIO(d.extract_image(xref)["image"]))
        W, H = img.size
        crop = img.crop((int(W * 0.15), int(H * 0.26), W, int(H * 0.96)))  # drop sidebar and browser chrome
        res = ocrmac.OCR(crop, language_preference=["es-ES", "en-US"], recognition_level="accurate").recognize()
        cw, ch = crop.size
        out[f"{key}-{i}"] = [[t, round(c, 2), [round(b[0] * cw), round((1 - b[1] - b[3]) * ch), round(b[2] * cw), round(b[3] * ch)]] for t, c, b in res]
    if len(sys.argv) >= 2: break
json.dump(out, open(os.path.join(OUT, "ocr.json" if len(sys.argv) < 2 else "ocr_test.json"), "w"), ensure_ascii=False)
print(len(out))
