import datetime as dt
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TYPES = {"security_training", "orientation", "setup", "mentor_1on1", "retro", "task", "meeting", "other"}
WORKDAYS = ["2026-12-07", "2026-12-08", "2026-12-09", "2026-12-10",
            "2026-12-14", "2026-12-15", "2026-12-16", "2026-12-17", "2026-12-18"]
REMOTE = {"2026-12-15", "2026-12-17"}


@pytest.fixture(scope="module")
def plan():
    return json.loads((ROOT / "onboarding.json").read_text(encoding="utf-8"))


def scheduled(plan):
    return [d for d in plan["days"] if d.get("items")]


def dates_with(plan, t):
    return {d["date"] for d in plan["days"] if any(i["type"] == t for i in d.get("items", []))}


def test_start_date(plan):
    assert plan["start_date"] == "2026-12-07"


def test_scheduled_dates_are_the_nine_workdays(plan):
    assert [d["date"] for d in scheduled(plan)] == WORKDAYS


def test_nothing_on_holiday_or_weekend(plan):
    for d in scheduled(plan):
        day = dt.date.fromisoformat(d["date"])
        assert day.weekday() < 5 and d["date"] != "2026-12-11"


def test_security_training_first_on_day1(plan):
    day1 = next(d for d in plan["days"] if d["date"] == "2026-12-07")
    assert day1["items"][0]["type"] == "security_training"


def test_setup_after_security_training(plan):
    day1 = next(d for d in plan["days"] if d["date"] == "2026-12-07")
    types = [i["type"] for i in day1["items"]]
    assert "setup" in types and types.index("setup") > types.index("security_training")


def test_orientation_second_wednesday(plan):
    assert dates_with(plan, "orientation") == {"2026-12-09"}


def test_locations(plan):
    loc = {d["date"]: d["location"] for d in scheduled(plan)}
    assert loc == {d: ("remote" if d in REMOTE else "office") for d in WORKDAYS}


def test_mentor_1on1_mon_thu(plan):
    assert dates_with(plan, "mentor_1on1") == {"2026-12-07", "2026-12-10", "2026-12-14", "2026-12-17"}


def test_retro_friday_or_last_workday(plan):
    assert dates_with(plan, "retro") == {"2026-12-10", "2026-12-18"}


def test_item_types_valid(plan):
    assert all(i["type"] in TYPES for d in plan["days"] for i in d.get("items", []))
