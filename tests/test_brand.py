import copy

import pytest

from pipeline import brand


@pytest.fixture()
def data():
    return brand.load_all()


def test_real_brand_files_are_valid():
    report = brand.validate()
    assert report.ok, report.errors
    assert not report.warnings, report.warnings


@pytest.mark.parametrize("name", sorted(brand.FILES))
def test_each_file_passes_its_schema(data, name):
    assert brand.schema_errors(data[name], brand.FILES[name][1]) == []


def test_schema_catches_a_bad_hex_and_missing_field(data):
    palette = copy.deepcopy(data["palette"])
    palette["colors"]["chai"]["hex"] = "peach"
    assert brand.schema_errors(palette, "palette.schema.json")
    character = copy.deepcopy(data["character"])
    del character["characters"]["chuski"]["flaw"]
    assert any("flaw" in e for e in brand.schema_errors(character, "character.schema.json"))


def mutate(data, change):
    broken = copy.deepcopy(data)
    change(broken)
    return brand.lint(broken)


def test_lint_enforces_the_guide(data):
    def high_eyes(d):
        d["character"]["characters"]["chuski"]["eyes"]["center_height"] = 0.6

    def plastic(d):
        d["character"]["characters"]["chuski"]["material"]["roughness"] = 0.2

    def black_eyes(d):
        d["palette"]["colors"]["eye"]["hex"] = "#000000"

    def chipmunk(d):
        d["character"]["characters"]["shakkar"]["voice"]["pitch_semitones"] = 12

    def short_hold(d):
        d["emotions"]["emotions"][0]["min_hold_frames"] = 10

    for change, words in [
        (high_eyes, "below the middle"),
        (plastic, "plastic"),
        (black_eyes, "pure black"),
        (chipmunk, "voice pitch"),
        (short_hold, "15 frames"),
    ]:
        report = mutate(data, change)
        assert any(words in e for e in report.errors), (words, report.errors)


def test_lint_checks_cross_references(data):
    def unknown_color(d):
        d["character"]["characters"]["chuski"]["material"]["color"] = "mango"

    def unknown_eyes(d):
        d["emotions"]["emotions"][1]["eyes"] = "laser"

    assert any("mango" in e for e in mutate(data, unknown_color).errors)
    assert any("laser" in e for e in mutate(data, unknown_eyes).errors)


def test_exactly_one_hero(data):
    def two_heroes(d):
        d["character"]["characters"]["shakkar"]["role"] = "hero"

    assert any("hero" in e for e in mutate(data, two_heroes).errors)
