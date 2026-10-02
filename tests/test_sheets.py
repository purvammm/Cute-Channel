import struct

import pytest

from pipeline import brand, sheets


@pytest.fixture(scope="module")
def data():
    return brand.load_all()


@pytest.fixture(scope="module")
def pal(data):
    return sheets.Palette(data["palette"])


def png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", png[16:24])


def test_every_emotion_and_view_draws_for_every_character(data, pal):
    for key, char in data["character"]["characters"].items():
        for emotion in data["emotions"]["emotions"]:
            for yaw in (0, 45, 90, 180):
                svg = sheets.draw_character(key, char, pal, 100, 200, 100, yaw, emotion, uid="t")
                assert svg.startswith("<ellipse") and svg.endswith("</g>")


def test_back_view_has_no_face(data, pal):
    chuski = data["character"]["characters"]["chuski"]
    front = sheets.draw_character("chuski", chuski, pal, 100, 200, 100, 0, uid="f")
    back = sheets.draw_character("chuski", chuski, pal, 100, 200, 100, 180, uid="b")
    ink = pal.hex("eye")
    assert front.count(f'fill="{ink}"') > back.count(f'fill="{ink}"')


def test_shy_blush_threshold(data):
    shakkar = data["character"]["characters"]["shakkar"]
    chuski = data["character"]["characters"]["chuski"]
    assert sheets.blush_opacity(shakkar, 0.4) == 0.0  # Shakkar hides mild feelings
    assert sheets.blush_opacity(shakkar, 1.0) == shakkar["blush"]["alpha"]
    assert sheets.blush_opacity(chuski, 0.4) == pytest.approx(0.2)


def test_unknown_variants_fail_loudly(pal):
    with pytest.raises(ValueError):
        sheets.draw_eye("laser", 0, 0, 10, 10, 1, 1, pal, [], "x")
    with pytest.raises(ValueError):
        sheets.draw_mouth("beak", 0, 0, 10, 2, 1, pal)


def test_wrap_never_breaks_words():
    lines = sheets.wrap("a drop of chai who hates going cold and loves rain", 12)
    assert all(len(line) <= 12 or " " not in line for line in lines)
    assert " ".join(lines) == "a drop of chai who hates going cold and loves rain"


def test_sheets_render_to_png(tmp_path):
    written = sheets.build_all(out_dir=tmp_path)
    sizes = {path.stem: png_size(path.read_bytes()) for path in written}
    assert sizes["character_sheet"] == (2400, 1500)
    assert sizes["thumbnail_test"] == (sheets.THUMB_SIZE[0] * 6, sheets.THUMB_SIZE[1] * 2)
    assert all(path.stat().st_size < 1_000_000 for path in written)
