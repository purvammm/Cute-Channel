import csv
from datetime import date, timedelta

from pipeline.paths import REPO_ROOT

PILLARS = {"trend", "relatable", "interactive", "food_asmr", "seasonal", "duo", "loop", "bts"}


def rows(name):
    with open(REPO_ROOT / "growth" / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_idea_bank_has_60_plus_unique_ideas():
    ideas = rows("idea_bank.csv")
    assert len(ideas) >= 60
    assert len({i["id"] for i in ideas}) == len(ideas)
    assert len({i["title"].lower() for i in ideas}) == len(ideas)
    assert {i["pillar"] for i in ideas} == PILLARS  # every pillar is represented


def test_production_starts_two_weeks_before_posting():
    for idea in rows("idea_bank.csv") + rows("calendar.csv"):
        posted = idea.get("post_by") or idea.get("date")
        if posted:
            start = date.fromisoformat(idea["start_production_by"])
            assert date.fromisoformat(posted) - start == timedelta(days=14), idea


def test_first_twelve_episodes_are_planned_in_order():
    planned = [i for i in rows("idea_bank.csv") if i["episode"]]
    assert [i["episode"] for i in planned] == [f"E{n:03d}" for n in range(1, 13)]
    assert all(i["status"] == "planned" and i["post_by"] for i in planned)
    assert {i["pillar"] for i in planned} == PILLARS  # all 8 pillars in the first 12


def test_scores_and_hooks():
    for idea in rows("idea_bank.csv"):
        assert idea["cost"] in {"S", "M", "L", "S-M"}
        for score in ("sendability", "hook_strength", "loop_potential"):
            assert 1 <= int(idea[score]) <= 5
        assert idea["hook_text"] and idea["hook_text"] == idea["hook_text"].strip()
