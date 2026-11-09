"""Build platform icons from a scalable Serpent ship drawing.

Install requirements-build.txt, then run this file from any directory.
--check validates the tracked exports without modifying them.
"""

import argparse
from io import BytesIO
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
MAC_BLOCKS = {'icp4': 16, 'icp5': 32, 'icp6': 64, 'ic07': 128,
              'ic08': 256, 'ic09': 512, 'ic10': 1024,
              'ic11': 32, 'ic12': 64, 'ic13': 256, 'ic14': 512}


def _ship(canvas, box, simple):
    """Icon-specific Serpent silhouette: swept wings, glass canopy, twin engines."""
    draw = ImageDraw.Draw(canvas)
    left, top, width, height = box

    def points(values):
        return [(left + x * width / 52, top + y * height / 68) for x, y in values]

    def polygon(values, fill, outline=None, stroke=0.8):
        vertices = points(values)
        draw.polygon(vertices, fill=fill)
        if outline:
            draw.line(vertices + vertices[:1], fill=outline,
                      width=max(1, round(stroke * width / 52)), joint='curve')

    navy, blue, edge = '#07172f', '#276aab', '#8de7ff'
    # Wide wings preserve the identity at taskbar sizes.
    for sign in (-1, 1):
        def side(values):
            return [(26 + sign * x, y) for x, y in values]
        polygon(side([(6, 21), (25, 36), (25, 47), (18, 44), (12, 58), (5, 48)]), navy, edge, 1.1)
        polygon(side([(8, 24), (22, 37), (15, 42), (9, 50)]), blue)
        if not simple:
            polygon(side([(9, 27), (19, 36), (14, 38)]), '#469bd4')
        polygon(side([(6, 43), (14, 47), (14, 61), (10, 66), (6, 61)]), '#113a66', '#60caff', 0.7)
        polygon(side([(7, 61), (13, 61), (11, 68), (9, 68)]), '#4bdcff')
        polygon(side([(9, 62), (11, 62), (10, 67)]), '#edffff')
    polygon([(26, 0), (33, 13), (36, 29), (33, 48), (29, 60),
             (23, 60), (19, 48), (16, 29), (19, 13)], '#174e82', edge, 1.1)
    polygon([(26, 3), (26, 55), (21, 45), (19, 28), (22, 13)], '#398dc3')
    polygon([(26, 12), (32, 20), (31, 29), (26, 34), (21, 29), (20, 20)], navy)
    polygon([(26, 15), (30, 21), (29, 27), (26, 31), (23, 27), (22, 21)], '#b4f4ff')
    if not simple:
        polygon([(26, 17), (27, 21), (26, 27), (24, 23)], '#ffffff')
        for sign in (-1, 1):
            for y in (38, 43, 48):
                draw.line(points([(26 + sign * 3, y), (26 + sign * 6, y + 1)]),
                          fill=navy, width=max(1, round(width / 52)))


def render_icon(size, platform='desktop'):
    # Supersample the vector shapes, rather than enlarge the gameplay bitmap.
    work = max(256, size * 2)
    canvas = Image.new('RGBA', (work, work))
    if platform == 'macos':
        inset = work * 0.098
        mask = Image.new('L', canvas.size)
        ImageDraw.Draw(mask).rounded_rectangle((inset, inset, work - inset, work - inset),
                                              radius=work * 0.18, fill=255)
        backdrop = Image.new('RGBA', canvas.size)
        draw = ImageDraw.Draw(backdrop)
        for y in range(work):
            t = y / work
            draw.line((0, y, work, y), fill=(round(17 - 9 * t), round(29 - 14 * t), round(58 - 23 * t), 255))
        backdrop.putalpha(mask)
        canvas.alpha_composite(backdrop)
        # A subtle keyline belongs to the dark tile, with no white outer frame.
        ImageDraw.Draw(canvas).rounded_rectangle((inset, inset, work - inset, work - inset),
                                                radius=work * 0.18, outline='#365278', width=max(1, work // 512))
        ship_height = work * 0.63
        ship_width = ship_height * 52 / 68
        top = work * 0.18
    else:
        ship_height = work * 0.88
        ship_width = ship_height * 52 / 68
        top = work * 0.055
    ship = Image.new('RGBA', canvas.size)
    _ship(ship, ((work - ship_width) / 2, top, ship_width, ship_height), simple=size <= 32)
    shadow = Image.new('RGBA', canvas.size, (2, 8, 23, 0))
    shadow.putalpha(ship.getchannel('A').filter(ImageFilter.GaussianBlur(work * 0.009)).point(lambda a: a * 0.45))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(ship)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def _png(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def build():
    runtime = ROOT / 'image/serpentis-icon.png'
    render_icon(512).save(runtime, optimize=True)
    frames = [render_icon(size) for size in WINDOWS_SIZES]
    frames[-1].save(ROOT / 'serpentis.ico', sizes=[(s, s) for s in WINDOWS_SIZES], append_images=frames[:-1])
    # PNG-backed ICNS chunks include explicit 1x and 2x representations.
    chunks = []
    images = {size: _png(render_icon(size, 'macos')) for size in set(MAC_BLOCKS.values())}
    for name, size in MAC_BLOCKS.items():
        payload = images[size]
        chunks.append(name.encode('ascii') + struct.pack('>I', len(payload) + 8) + payload)
    body = b''.join(chunks)
    (ROOT / 'serpentis.icns').write_bytes(b'icns' + struct.pack('>I', len(body) + 8) + body)


def check():
    with Image.open(ROOT / 'image/serpentis-icon.png') as icon:
        if icon.size != (512, 512) or icon.convert('RGBA').getpixel((0, 0))[3] != 0:
            raise ValueError('Runtime icon must be transparent and 512 x 512')
        if icon.convert('RGBA').tobytes() != render_icon(512).tobytes():
            raise ValueError('Runtime icon is stale')
    with Image.open(ROOT / 'serpentis.ico') as icon:
        if icon.ico.sizes() != {(s, s) for s in WINDOWS_SIZES}:
            raise ValueError('Windows icon is missing a required size')
        for size in WINDOWS_SIZES:
            frame = icon.ico.getimage((size, size)).convert('RGBA')
            if frame.tobytes() != render_icon(size).tobytes():
                raise ValueError(f'Windows {size}px icon is stale')
    with Image.open(ROOT / 'serpentis.icns') as icon:
        for size in icon.info['sizes']:
            pixels = icon.icns.getimage(size).convert('RGBA')
            if pixels.tobytes() != render_icon(pixels.width, 'macos').tobytes():
                raise ValueError(f'Mac {size} icon is stale')
        if len(icon.info['sizes']) != len(MAC_BLOCKS):
            raise ValueError('Mac icon is missing a required representation')


def preview(path):
    sheet = Image.new('RGB', (1080, 560), '#e8edf4')
    draw = ImageDraw.Draw(sheet)
    for i, label in enumerate(('macOS', 'Windows / light', 'Linux / dark')):
        x = i * 360
        draw.rounded_rectangle((x + 16, 16, x + 344, 544), radius=18,
                               fill='#151d30' if i == 2 else '#f7f9fc')
        draw.text((x + 32, 36), label, fill='#e1edff' if i == 2 else '#1a2c48', font_size=22)
        icon = render_icon(256, 'macos' if i == 0 else 'desktop')
        sheet.paste(icon, (x + 52, 92), icon)
        cursor = x + 44
        for size in (64, 32, 24, 16):
            icon = render_icon(size, 'macos' if i == 0 else 'desktop')
            sheet.paste(icon, (cursor, 405 + (64 - size) // 2), icon)
            draw.text((cursor, 486), str(size), fill='#95a8c5' if i == 2 else '#506581', font_size=14)
            cursor += 78
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    if not args.check:
        build()
    check()
    if args.preview:
        preview(args.preview)
    print('Verified Serpentis icons: macOS ICNS, Windows ICO and runtime/Linux PNG')
