"""Tracked icons expose real native-size artwork, including alpha and tiny sizes."""

from pathlib import Path
import struct

import pygame

ROOT = Path(__file__).resolve().parents[1]
PNG = b'\x89PNG\r\n\x1a\n'


def png_size(data):
    assert data.startswith(PNG)
    assert data[12:16] == b'IHDR'
    return struct.unpack('>II', data[16:24])


def test_windows_icon_contains_every_taskbar_and_dpi_size():
    data = (ROOT / 'serpentis.ico').read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    assert (reserved, kind, count) == (0, 1, 9)
    sizes = set()
    for index in range(count):
        w, h, _, _, _, bits, length, offset = struct.unpack_from('<BBBBHHII', data, 6 + 16 * index)
        size = w or 256, h or 256
        assert bits == 32
        assert png_size(data[offset:offset + length]) == size
        assert offset + length <= len(data)
        sizes.add(size)
    assert sizes == {(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)}


def test_mac_icon_contains_standard_and_retina_png_representations():
    data = (ROOT / 'serpentis.icns').read_bytes()
    assert data[:4] == b'icns'
    assert struct.unpack('>I', data[4:8])[0] == len(data)
    expected = {b'icp4': 16, b'icp5': 32, b'icp6': 64, b'ic07': 128,
                b'ic08': 256, b'ic09': 512, b'ic10': 1024,
                b'ic11': 32, b'ic12': 64, b'ic13': 256, b'ic14': 512}
    offset, seen = 8, set()
    while offset < len(data):
        kind, length = struct.unpack_from('>4sI', data, offset)
        assert kind in expected and kind not in seen
        assert length > 8 and offset + length <= len(data)
        assert png_size(data[offset + 8:offset + length]) == (expected[kind],) * 2
        seen.add(kind)
        offset += length
    assert seen == set(expected)
    assert offset == len(data)


def test_runtime_and_linux_icon_has_transparent_corners_and_a_large_visible_ship(pygame_context):
    icon = pygame.image.load(str(ROOT / 'image/serpentis-icon.png'))
    assert icon.get_size() == (512, 512)
    for point in ((0, 0), (511, 0), (0, 511), (511, 511)):
        assert icon.get_at(point).a == 0
    hull = icon.get_bounding_rect(min_alpha=200)
    assert hull.height >= 400
    assert hull.width >= 300
