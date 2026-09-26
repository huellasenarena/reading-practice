"""Draw the home-screen icons: a white Georgia "R" on black, like the favicon."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "icons"
FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"

for size in (180, 192, 512):
    img = Image.new("RGB", (size, size), "#111111")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(size * 0.62))
    draw.text((size / 2, size / 2), "R", font=font, fill="#ffffff", anchor="mm")
    img.save(OUT / f"icon-{size}.png", optimize=True)
