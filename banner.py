#!/usr/bin/env python3
"""
Sideways ASCII banner printer for dot-matrix/lpr.

- Uses a 5x7 bitmap font (pixels drawn using the character itself)
- Renders the text horizontally, then rotates 90° so letters print sideways
- Centers the result within an integer number of pages after rotation
- Page geometry is configurable (default: 80 lines x 66 columns per page)
- Can print via `lpr` or preview to stdout

Usage examples:
  python3 banner.py "HELLO WORLD" --preview
  python3 banner.py "AP CSA ROCKS" --printer
  python3 banner.py "VEX ROBOTICS" --cols 66 --lines 80 --rotate cw --preview
"""

import math
import subprocess
from typing import Dict, Tuple, List

GLYPH_W = 5
GLYPH_H = 7

MARGIN_DEFAULT = 5  # vertical top/bottom margin in lines
SIDE_MARGIN_DEFAULT = 10  # horizontal left/right margin in columns (for width-fill)

# 5x7 font: each tuple has 7 rows; each row is a 5-bit integer (bit 4 = leftmost).
# Glyphs are blocky but readable when rotated.
FONT_5X7: Dict[str, Tuple[int, int, int, int, int, int, int]] = {
    " ": (0,0,0,0,0,0,0),
    "0": (0b01110,0b10001,0b10011,0b10101,0b11001,0b10001,0b01110),
    "1": (0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110),
    "2": (0b01110,0b10001,0b00001,0b00110,0b01000,0b10000,0b11111),
    "3": (0b11110,0b00001,0b00001,0b01110,0b00001,0b00001,0b11110),
    "4": (0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010),
    "5": (0b11111,0b10000,0b11110,0b00001,0b00001,0b10001,0b01110),
    "6": (0b00110,0b01000,0b10000,0b11110,0b10001,0b10001,0b01110),
    "7": (0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000),
    "8": (0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110),
    "9": (0b01110,0b10001,0b10001,0b01111,0b00001,0b00010,0b01100),

    "A": (0b01110,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001),
    "B": (0b11110,0b10001,0b10001,0b11110,0b10001,0b10001,0b11110),
    "C": (0b01110,0b10001,0b10000,0b10000,0b10000,0b10001,0b01110),
    "D": (0b11100,0b10010,0b10001,0b10001,0b10001,0b10010,0b11100),
    "E": (0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b11111),
    "F": (0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b10000),
    "G": (0b01110,0b10001,0b10000,0b10111,0b10001,0b10001,0b01110),
    "H": (0b10001,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001),
    "I": (0b01110,0b00100,0b00100,0b00100,0b00100,0b00100,0b01110),
    "J": (0b00111,0b00010,0b00010,0b00010,0b10010,0b10010,0b01100),
    "K": (0b10001,0b10010,0b10100,0b11000,0b10100,0b10010,0b10001),
    "L": (0b10000,0b10000,0b10000,0b10000,0b10000,0b10000,0b11111),
    "M": (0b10001,0b11011,0b10101,0b10101,0b10001,0b10001,0b10001),
    "N": (0b10001,0b10001,0b11001,0b10101,0b10011,0b10001,0b10001),
    "O": (0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110),
    "P": (0b11110,0b10001,0b10001,0b11110,0b10000,0b10000,0b10000),
    "Q": (0b01110,0b10001,0b10001,0b10001,0b10101,0b10010,0b01101),
    "R": (0b11110,0b10001,0b10001,0b11110,0b10100,0b10010,0b10001),
    "S": (0b01111,0b10000,0b10000,0b01110,0b00001,0b00001,0b11110),
    "T": (0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b00100),
    "U": (0b10001,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110),
    "V": (0b10001,0b10001,0b10001,0b10001,0b10001,0b01010,0b00100),
    "W": (0b10001,0b10001,0b10001,0b10101,0b10101,0b11011,0b10001),
    "X": (0b10001,0b10001,0b01010,0b00100,0b01010,0b10001,0b10001),
    "Y": (0b10001,0b10001,0b01010,0b00100,0b00100,0b00100,0b00100),
    "Z": (0b11111,0b00001,0b00010,0b00100,0b01000,0b10000,0b11111),

    "!": (0b00100,0b00100,0b00100,0b00100,0b00100,0b00000,0b00100),
    "?": (0b01110,0b10001,0b00001,0b00110,0b00100,0b00000,0b00100),
    ".": (0b00000,0b00000,0b00000,0b00000,0b00000,0b00110,0b00110),
    "-": (0b00000,0b00000,0b00000,0b01110,0b00000,0b00000,0b00000),
    ":": (0b00000,0b00110,0b00110,0b00000,0b00110,0b00110,0b00000),
}

def glyph_for(ch: str) -> Tuple[int, ...]:
    return FONT_5X7.get(ch, FONT_5X7[" "])
    
def scale_bitmap(bitmap, zoom: int) -> List[List[str]]:
    """
    Nearest-neighbor scale: duplicate each pixel zoom times horizontally
    and each row zoom times vertically.
    """
    if zoom <= 1:
        return bitmap  # no scaling needed

    scaled = []
    for row in bitmap:
        new_row = []
        for ch in row:
            new_row.extend([ch] * int(zoom * (3/5)))  # widen pixels
        for _ in range(zoom):
            scaled.append(new_row[:])    # duplicate rows
    return scaled

def compute_auto_zoom(text: str,
                      page_lines: int,
                      page_cols: int,
                      h_space: int,
                      margin_lines: int = MARGIN_DEFAULT,
                      side_margin_cols: int = SIDE_MARGIN_DEFAULT) -> int:
    """
    Auto-zoom:
      1) Try to fit the whole banner within ONE page vertically (with margin_lines top/bottom).
      2) If impossible, width-fill while leaving side_margin_cols on left/right.
    Guarantees zoom >= 1.
    """
    text = (text or "").upper()
    n = len(text)
    if n == 0:
        return 1

    usable_lines = max(0, page_lines - 2*margin_lines)
    denom_height_per_zoom = n*GLYPH_W + (n-1)*h_space  # rotated vertical height per zoom

    zoom_by_height = (usable_lines // denom_height_per_zoom) if denom_height_per_zoom > 0 else 1
    zoom_by_width  = max(1, (page_cols - 2*side_margin_cols) // GLYPH_H)  # GLYPH_H=7

    if zoom_by_height >= 1:
        return min(zoom_by_height, zoom_by_width)

    # Can't fit on one page -> width-fill with side margins
    return zoom_by_width

def render_line_to_bitmap(text: str, h_space: int = 1) -> List[List[str]]:
    """
    Build a 2D bitmap (rows=GLYPH_H, cols=total width) using the *character itself* as the pixel.
    """
    text = text.upper()
    cols = len(text) * (GLYPH_W + h_space) - (h_space if text else 0)
    bitmap = [[" " for _ in range(cols)] for _ in range(GLYPH_H)]
    x = 0
    for ch in text:
        bits = glyph_for(ch)
        for row in range(GLYPH_H):
            row_bits = bits[row]
            for bit in range(GLYPH_W):
                if row_bits & (1 << (GLYPH_W - 1 - bit)):
                    bitmap[row][x + bit] = ch  # pixel uses the character itself
        x += GLYPH_W + h_space
    return bitmap

def rotate_bitmap(bitmap: List[List[str]], direction: str = "cw") -> List[List[str]]:
    """
    Rotate 90 degrees. After rotation:
      - width becomes original height (7)
      - height becomes original width (many lines)
    """
    rows = len(bitmap)
    cols = len(bitmap[0]) if rows else 0
    if direction.lower() == "cw":
        return [[bitmap[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]
    # default ccw
    return [[bitmap[r][cols - 1 - c] for r in range(rows)] for c in range(cols)]

def center_on_pages(rot: List[List[str]],
                    page_lines: int = 66,
                    page_cols: int = 80) -> List[str]:
    """
    Center the rotated banner:
      - Horizontally: center rot width within page_cols
      - Vertically: pad to a multiple of page_lines (integer number of pages),
        centering the content across those pages.
    Returns a list of strings, each exactly page_cols characters long.
    """
    rot_h = len(rot)                  # number of output lines (vertical)
    rot_w = len(rot[0]) if rot_h else 0  # width in characters (typically 7)

    # Horizontal centering (per line)
    if rot_w > page_cols:
        # If someone scales glyphs later and exceeds page width, clip (or raise)
        # Here we clip to fit, old-school banner style.
        left = 0
        right = page_cols
        rot = [row[left:right] for row in rot]
        rot_w = page_cols

    left_pad = (page_cols - rot_w) // 2
    right_pad = page_cols - rot_w - left_pad
    line_pad_left = " " * left_pad
    line_pad_right = " " * right_pad

    # Vertical centering to integer number of pages
    pages = max(1, math.ceil(rot_h / page_lines))
    total_lines = pages * page_lines
    top_pad = (total_lines - rot_h) // 2
    bottom_pad = total_lines - rot_h - top_pad

    out: List[str] = []
    out.extend([" " * page_cols] * top_pad)
    for r in rot:
        out.append(line_pad_left + "".join(r) + line_pad_right)
    out.extend([" " * page_cols] * bottom_pad)
    return out

def banner_lines(text: str,
                 page_lines: int = 66,      # 66 lines tall
                 page_cols: int = 80,       # 80 columns wide
                 rotate: str = "cw",
                 h_space: int = 1,
                 zoom: int = 0,
                 margin: int = MARGIN_DEFAULT,
                 side_margin_cols: int = SIDE_MARGIN_DEFAULT) -> List[str]:
    """
    If zoom <= 0, pick an integer zoom:
      - Prefer single-page height fit with top/bottom margin.
      - Else width-fill with left/right side margin.
    """
    if zoom <= 0:
        zoom = compute_auto_zoom(text, page_lines, page_cols, h_space,
                                 margin_lines=margin, side_margin_cols=side_margin_cols)

    bmp = render_line_to_bitmap(text, h_space=h_space)
    bmp = scale_bitmap(bmp, zoom=zoom)
    rot = rotate_bitmap(bmp, direction=rotate)
    return center_on_pages(rot, page_lines=page_lines, page_cols=page_cols)

def send_to_lpr(lines: List[str], printer: str = None) -> None:
    """
    Pipe the lines to lpr. If `printer` is provided, passes -P <printer>.
    """
    cmd = ["lpr"]
    if printer:
        cmd += ["-P", printer]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, encoding="utf-8")
    try:
        proc.communicate("\n".join(lines) + "\n")
    finally:
        proc.wait()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sideways ASCII banner -> lpr")
    parser.add_argument("--lines", type=int, default=80, help="Lines per page (default: 80)")
    parser.add_argument("--cols", type=int, default=66, help="Columns per page (default: 66)")
    parser.add_argument("--rotate", choices=["ccw", "cw"], default="cw", help="Rotate 90° (default: cw)")
    parser.add_argument("--zoom", type=int, default=0, help="Integer zoom; 0=auto to hit ~5-line margins (default)")
    parser.add_argument("--margin", type=int, default=5, help="Top/bottom margin in lines for auto-zoom")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preview", action="store_true", help="Print to stdout instead of lpr")
    group.add_argument("--printer", nargs="?", const="", help="Send to lpr (optionally specify printer name)")
    args = parser.parse_args()

    lines = banner_lines(args.text,
                         page_lines=args.lines,
                         page_cols=args.cols,
                         rotate=args.rotate,
                         h_space=args.space,
                         zoom=args.zoom,
                         margin=args.margin)

    if args.preview or not args.printer:
        for i, line in enumerate(lines, 1):
            print(line)
            if i % args.lines == 0 and i != len(lines):
                print("-" * args.cols)
    else:
        send_to_lpr(lines, printer=(args.printer or None))

def test_banner():
    # 66 lines x 80 columns page, CW rotation
    # side_margin_cols=5 -> width-fill picks zoom=floor((80 - 10)/7)=10 -> 7*10 = 70
    lines = banner_lines("Happy Birthday Brian",
                         page_lines=66, page_cols=80,
                         rotate="cw", h_space=1,
                         zoom=0,           # auto
                         margin=5,         # top/bottom lines
                         side_margin_cols=16)  # left/right columns
                         
    pages = 1

    print("+" + "-"*80 + "+")
    for i, line in enumerate(lines, 1):
        print("|" + line + "|")
        if i % 66 == 0 and i != len(lines):
            print("+" + "-"*80 + "+\n" + "+" + "-"*80 + "+")
            pages += 1
    print("+" + "-"*80 + "+")
    print(f"{pages=}")





if __name__ == "__main__":
    #main()
    test_banner()