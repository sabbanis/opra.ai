"""Render the README launch GIF without third-party dependencies."""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Iterable


WIDTH = 720
HEIGHT = 336
FRAME_COUNT = 36
DELAY_CS = 5

PALETTE = [
    (8, 13, 28),  # 0 bg
    (19, 28, 48),  # 1 grid
    (15, 23, 42),  # 2 panel
    (71, 85, 105),  # 3 muted
    (226, 232, 240),  # 4 text
    (34, 211, 238),  # 5 cyan
    (34, 197, 94),  # 6 green
    (245, 158, 11),  # 7 amber
    (251, 113, 133),  # 8 rose
    (96, 165, 250),  # 9 blue
    (255, 255, 255),  # 10 white
    (2, 6, 23),  # 11 shadow
    (167, 139, 250),  # 12 violet
    (20, 184, 166),  # 13 teal
    (51, 65, 85),  # 14 slate
    (148, 163, 184),  # 15 soft
]

BG = 0
GRID = 1
PANEL = 2
MUTED = 3
TEXT = 4
CYAN = 5
GREEN = 6
AMBER = 7
ROSE = 8
BLUE = 9
WHITE = 10
SHADOW = 11
VIOLET = 12
TEAL = 13
SLATE = 14
SOFT = 15

NODES = [
    ("INTENT", 86, 138, CYAN),
    ("POLICY", 220, 138, GREEN),
    ("REVIEW", 354, 138, BLUE),
    ("STATE", 488, 138, VIOLET),
    ("AUDIT", 622, 138, AMBER),
]

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


def put(frame: bytearray, x: int, y: int, color: int) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        frame[y * WIDTH + x] = color


def rect(frame: bytearray, x: int, y: int, w: int, h: int, color: int) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + w)
    y1 = min(HEIGHT, y + h)
    for yy in range(y0, y1):
        start = yy * WIDTH + x0
        frame[start : start + (x1 - x0)] = bytes([color]) * (x1 - x0)


def circle(frame: bytearray, cx: int, cy: int, r: int, color: int, fill: bool = True) -> None:
    rr = r * r
    inner = max(0, r - 2) ** 2
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = (x - cx) * (x - cx) + (y - cy) * (y - cy)
            if d <= rr and (fill or d >= inner):
                put(frame, x, y, color)


def line(frame: bytearray, x0: int, y0: int, x1: int, y1: int, color: int, width: int = 1) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x = x0
    y = y0
    radius = max(0, width // 2)
    while True:
        if radius:
            circle(frame, x, y, radius, color)
        else:
            put(frame, x, y, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def polygon(frame: bytearray, points: list[tuple[int, int]], color: int) -> None:
    min_y = max(0, min(y for _, y in points))
    max_y = min(HEIGHT - 1, max(y for _, y in points))
    for y in range(min_y, max_y + 1):
        xs: list[int] = []
        for i, (x1, y1) in enumerate(points):
            x2, y2 = points[(i + 1) % len(points)]
            if y1 == y2:
                continue
            if min(y1, y2) <= y < max(y1, y2):
                xs.append(int(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
        xs.sort()
        for i in range(0, len(xs), 2):
            if i + 1 < len(xs):
                line(frame, xs[i], y, xs[i + 1], y, color)


def text_width(value: str, scale: int) -> int:
    return sum((6 if char != " " else 4) * scale for char in value) - scale


def draw_text(frame: bytearray, value: str, x: int, y: int, color: int, scale: int = 2) -> None:
    cursor = x
    for char in value.upper():
        if char == " ":
            cursor += 4 * scale
            continue
        glyph = FONT.get(char)
        if glyph is None:
            cursor += 6 * scale
            continue
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    rect(frame, cursor + col * scale, y + row * scale, scale, scale, color)
        cursor += 6 * scale


def draw_check(frame: bytearray, x: int, y: int, color: int, width: int = 4) -> None:
    line(frame, x, y, x + 10, y + 10, color, width)
    line(frame, x + 10, y + 10, x + 29, y - 12, color, width)


def draw_node_shell(
    frame: bytearray,
    cx: int,
    cy: int,
    color: int,
    active: bool,
    complete: bool,
) -> None:
    if active:
        circle(frame, cx, cy, 44, color)
        circle(frame, cx, cy, 39, BG)
    else:
        circle(frame, cx, cy, 39, SLATE)
        circle(frame, cx, cy, 36, BG)
    circle(frame, cx, cy, 31, PANEL)
    if complete:
        circle(frame, cx + 27, cy - 27, 12, GREEN)
        draw_check(frame, cx + 20, cy - 27, WHITE, 2)


def draw_intent(frame: bytearray, cx: int, cy: int, color: int) -> None:
    circle(frame, cx - 16, cy - 8, 11, color)
    rect(frame, cx - 31, cy + 7, 30, 24, color)
    rect(frame, cx + 8, cy - 21, 28, 28, color)
    rect(frame, cx + 13, cy - 15, 6, 6, BG)
    rect(frame, cx + 25, cy - 15, 6, 6, BG)
    line(frame, cx + 22, cy - 21, cx + 22, cy - 33, color, 3)
    circle(frame, cx + 22, cy - 36, 4, color)
    line(frame, cx + 13, cy + 4, cx + 31, cy + 4, BG, 3)


def draw_policy(frame: bytearray, cx: int, cy: int, color: int) -> None:
    points = [
        (cx, cy - 34),
        (cx + 32, cy - 20),
        (cx + 25, cy + 24),
        (cx, cy + 39),
        (cx - 25, cy + 24),
        (cx - 32, cy - 20),
    ]
    polygon(frame, points, color)
    polygon(frame, [(cx, cy - 24), (cx + 21, cy - 14), (cx + 16, cy + 18), (cx, cy + 29), (cx - 16, cy + 18), (cx - 21, cy - 14)], PANEL)
    draw_check(frame, cx - 14, cy + 4, color, 4)


def draw_review(frame: bytearray, cx: int, cy: int, color: int) -> None:
    line(frame, cx - 22, cy - 29, cx - 22, cy + 30, color, 5)
    circle(frame, cx - 22, cy - 29, 10, color)
    circle(frame, cx - 22, cy + 30, 10, color)
    line(frame, cx - 18, cy - 3, cx + 24, cy - 25, color, 5)
    circle(frame, cx + 30, cy - 29, 10, color)
    line(frame, cx - 18, cy + 5, cx + 24, cy + 27, color, 5)
    circle(frame, cx + 30, cy + 30, 10, color)


def draw_state(frame: bytearray, cx: int, cy: int, color: int) -> None:
    rect(frame, cx - 31, cy - 31, 46, 58, color)
    rect(frame, cx - 24, cy - 22, 32, 6, PANEL)
    rect(frame, cx - 24, cy - 8, 32, 6, PANEL)
    rect(frame, cx - 24, cy + 6, 24, 6, PANEL)
    rect(frame, cx - 9, cy - 20, 44, 58, BG)
    rect(frame, cx - 4, cy - 16, 40, 54, color)
    rect(frame, cx + 3, cy - 6, 26, 5, PANEL)
    rect(frame, cx + 3, cy + 7, 26, 5, PANEL)
    rect(frame, cx + 3, cy + 20, 18, 5, PANEL)


def draw_audit(frame: bytearray, cx: int, cy: int, color: int) -> None:
    rect(frame, cx - 31, cy - 35, 62, 70, color)
    rect(frame, cx - 24, cy - 26, 48, 52, PANEL)
    draw_check(frame, cx - 15, cy - 1, GREEN, 4)
    rect(frame, cx + 3, cy + 9, 7, 12, color)
    rect(frame, cx + 14, cy + 2, 7, 19, color)
    rect(frame, cx + 25, cy - 8, 7, 29, color)


def draw_dashboard(frame: bytearray, progress: float) -> None:
    rect(frame, 166, 246, 388, 56, SHADOW)
    rect(frame, 170, 242, 388, 56, PANEL)
    draw_text(frame, "DASHBOARD", 193, 264, SOFT, 2)
    bars = [
        (354, 281, 37, CYAN),
        (409, 272, 46, GREEN),
        (464, 286, 30, AMBER),
        (519, 263, 52, VIOLET),
    ]
    for index, (x, y, h, color) in enumerate(bars):
        active = progress > 0.72 + index * 0.05
        rect(frame, x, 290 - h, 15, h, color if active else SLATE)
    if progress > 0.9:
        circle(frame, 536, 264, 11, GREEN)
        draw_check(frame, 529, 264, WHITE, 2)


def draw_base(frame: bytearray, progress: float) -> None:
    for y in range(42, HEIGHT, 34):
        line(frame, 30, y, WIDTH - 30, y, GRID)
    for x in range(55, WIDTH, 55):
        line(frame, x, 30, x, HEIGHT - 30, GRID)
    rect(frame, 40, 44, 640, 198, SHADOW)
    rect(frame, 35, 39, 640, 198, PANEL)
    draw_text(frame, "GOVERNED WRITE PATH", 224, 64, TEXT, 2)

    for index in range(len(NODES) - 1):
        _, x0, y0, _ = NODES[index]
        _, x1, y1, _ = NODES[index + 1]
        line(frame, x0 + 42, y0, x1 - 42, y1, SLATE, 4)
        if progress > index / 4:
            local = min(1.0, max(0.0, progress * 4 - index))
            line(frame, x0 + 42, y0, int((x0 + 42) + (x1 - x0 - 84) * local), y1, CYAN, 4)

    for index, (label, cx, cy, color) in enumerate(NODES):
        active = index / 4 <= progress <= (index + 0.8) / 4
        complete = progress > (index + 0.55) / 4
        draw_node_shell(frame, cx, cy, color, active, complete)
        if label == "INTENT":
            draw_intent(frame, cx, cy, color)
        elif label == "POLICY":
            draw_policy(frame, cx, cy, color)
        elif label == "REVIEW":
            draw_review(frame, cx, cy, color)
        elif label == "STATE":
            draw_state(frame, cx, cy, color)
        else:
            draw_audit(frame, cx, cy, color)
        label_x = cx - text_width(label, 1) // 2
        draw_text(frame, label, label_x, cy + 49, SOFT if not active else WHITE, 1)

    draw_dashboard(frame, progress)


def request_position(progress: float) -> tuple[int, int]:
    points = [(86, 138), (220, 138), (354, 138), (488, 138), (622, 138)]
    scaled = progress * (len(points) - 1)
    index = min(len(points) - 2, int(scaled))
    local = scaled - index
    x0, y0 = points[index]
    x1, y1 = points[index + 1]
    lift = int(math.sin(local * math.pi) * 22)
    return int(x0 + (x1 - x0) * local), int(y0 + (y1 - y0) * local - lift)


def draw_request(frame: bytearray, progress: float, frame_index: int) -> None:
    x, y = request_position(progress)
    color = CYAN if frame_index % 8 < 4 else WHITE
    rect(frame, x - 18, y - 11, 36, 22, color)
    rect(frame, x - 13, y - 6, 26, 12, BG)
    line(frame, x - 13, y - 6, x, y + 3, color, 2)
    line(frame, x + 13, y - 6, x, y + 3, color, 2)


def render_frame(frame_index: int) -> bytearray:
    frame = bytearray([BG]) * (WIDTH * HEIGHT)
    progress = frame_index / (FRAME_COUNT - 1)
    eased = 0.5 - math.cos(progress * math.pi) / 2
    draw_base(frame, eased)
    draw_request(frame, eased, frame_index)
    return frame


def lzw_compress(indices: Iterable[int], min_code_size: int) -> bytes:
    """Write simple root-color GIF LZW codes with frequent clears.

    This is larger than dictionary compression, but it stays compatible with
    conservative GIF decoders and keeps the README asset reproducible without
    Pillow, ImageMagick, or ffmpeg.
    """

    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    bit_buffer = 0
    bit_count = 0
    output = bytearray()

    def write_code(code: int) -> None:
        nonlocal bit_buffer, bit_count
        bit_buffer |= code << bit_count
        bit_count += code_size
        while bit_count >= 8:
            output.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bit_count -= 8

    codes_since_clear = 0
    write_code(clear)
    for value in indices:
        if codes_since_clear >= 8:
            write_code(clear)
            codes_since_clear = 0
        write_code(value)
        codes_since_clear += 1
    write_code(end)
    if bit_count:
        output.append(bit_buffer & 0xFF)
    return bytes(output)


def sub_blocks(data: bytes) -> bytes:
    result = bytearray()
    for index in range(0, len(data), 255):
        block = data[index : index + 255]
        result.append(len(block))
        result.extend(block)
    result.append(0)
    return bytes(result)


def frame_region(
    frame: bytearray,
    previous: bytearray | None,
) -> tuple[int, int, int, int, bytearray]:
    if previous is None:
        return 0, 0, WIDTH, HEIGHT, frame

    left = WIDTH
    top = HEIGHT
    right = -1
    bottom = -1
    for y in range(HEIGHT):
        row = y * WIDTH
        for x in range(WIDTH):
            if frame[row + x] != previous[row + x]:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

    if right < left or bottom < top:
        return 0, 0, 1, 1, bytearray([frame[0]])

    width = right - left + 1
    height = bottom - top + 1
    patch = bytearray()
    for y in range(top, bottom + 1):
        row = y * WIDTH
        patch.extend(frame[row + left : row + right + 1])
    return left, top, width, height, patch


def write_gif(path: Path, frames: list[bytearray]) -> None:
    min_code_size = 4
    color_table = PALETTE + [(0, 0, 0)] * (16 - len(PALETTE))
    data = bytearray()
    data.extend(b"GIF89a")
    data.extend(struct.pack("<HH", WIDTH, HEIGHT))
    data.extend(bytes([0xF3, BG, 0]))
    for red, green, blue in color_table:
        data.extend(bytes([red, green, blue]))
    data.extend(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
    previous: bytearray | None = None
    for frame in frames:
        left, top, width, height, patch = frame_region(frame, previous)
        data.extend(b"\x21\xF9\x04")
        data.extend(bytes([0x00]))
        data.extend(struct.pack("<H", DELAY_CS))
        data.extend(bytes([0, 0]))
        data.extend(b"\x2C")
        data.extend(struct.pack("<HHHH", left, top, width, height))
        data.extend(bytes([0]))
        compressed = lzw_compress(patch, min_code_size)
        data.extend(bytes([min_code_size]))
        data.extend(sub_blocks(compressed))
        previous = frame
    data.extend(b"\x3B")
    path.write_bytes(bytes(data))


def main() -> int:
    output = Path("docs/assets/opra-launch-loop.gif")
    frames = [render_frame(index) for index in range(FRAME_COUNT)]
    write_gif(output, frames)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
