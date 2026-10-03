import pytest

from blender.lib import colors


def test_hex_to_srgb():
    assert colors.hex_to_srgb("#ffffff") == (1.0, 1.0, 1.0)
    assert colors.hex_to_srgb("000") == (0.0, 0.0, 0.0)
    assert colors.hex_to_srgb("#FAB") == colors.hex_to_srgb("#ffaabb")


def test_hex_to_linear_uses_the_srgb_curve():
    r, g, b = colors.hex_to_linear("#808080")
    assert r == g == b == pytest.approx(0.2158605, abs=1e-6)
    assert colors.srgb_to_linear(0.04) == pytest.approx(0.04 / 12.92)


@pytest.mark.parametrize("bad", ["#12", "#gggggg", "", "#1234567"])
def test_bad_hex_codes_raise(bad):
    with pytest.raises(ValueError):
        colors.hex_to_srgb(bad)
