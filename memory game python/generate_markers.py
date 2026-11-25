"""
Make a printable A4 sheet of the game cards: IDs 0, 1, 2 twice each, plus two
spare IDs (3, 4) for testing the "no partner" error path.

    python3 generate_markers.py                 # -> aruco_cards_A4.pdf and .png
    python3 generate_markers.py --size-mm 50

Print at 100 % / "actual size" (not "fit to page"), then check one marker with a
ruler. Stick the cards on matte card so the room lights don't reflect.
"""
import argparse

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

DPI = 300
MM = DPI / 25.4


def mm(v):
    return int(round(v * MM))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size-mm", type=float, default=55.0, help="black marker edge length")
    ap.add_argument("--ids", type=int, nargs="+", default=[0, 0, 1, 1, 2, 2, 3, 4])
    ap.add_argument("--out", default="aruco_cards_A4")
    a = ap.parse_args()

    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    page = Image.new("L", (mm(210), mm(297)), 255)
    draw = ImageDraw.Draw(page)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", mm(4))
    except OSError:
        font = ImageFont.load_default()

    card_w, card_h = 85.0, 70.0       # cut size of each card [mm]
    x0, y0 = (210 - 2 * card_w) / 2, 8.0
    for k, mid in enumerate(a.ids):
        col, row = k % 2, k // 2
        cx, cy = x0 + col * card_w, y0 + row * card_h
        if cy + card_h > 297:
            raise SystemExit("Too many cards for one page")
        draw.rectangle([mm(cx), mm(cy), mm(cx + card_w), mm(cy + card_h)], outline=160, width=2)  # cut line
        side = mm(a.size_mm)
        if hasattr(cv2.aruco, "generateImageMarker"):
            img = cv2.aruco.generateImageMarker(dictionary, mid, side)
        else:
            img = cv2.aruco.drawMarker(dictionary, mid, side)
        mx = mm(cx + (card_w - a.size_mm) / 2)
        my = mm(cy + 5)
        page.paste(Image.fromarray(img), (mx, my))
        label = f"ID {mid}" + ("  (spare)" if k >= 6 else "") + f"   {a.size_mm:g} mm"
        draw.text((mm(cx + 4), mm(cy + card_h - 7)), label, fill=90, font=font)

    draw.text((mm(10), mm(290)), "Print at 100% / actual size. DICT_4X4_50.", fill=90, font=font)
    page.save(a.out + ".png", dpi=(DPI, DPI))
    page.save(a.out + ".pdf", resolution=DPI)
    print(f"wrote {a.out}.pdf and {a.out}.png")


if __name__ == "__main__":
    main()
