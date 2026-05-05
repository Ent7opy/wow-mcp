import json
from pathlib import Path

from wow_mcp.parsers import flatten_equipped_item, extract_profession_tier


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_flatten_equipped_item_full_fields():
    items = load("equipment.json")["equipped_items"]
    assert flatten_equipped_item(items[0]) == {
        "slot": "HEAD",
        "name": "Helm of Testing",
        "item_level": 489,
        "quality": "EPIC",
    }


def test_flatten_equipped_item_missing_optional_fields():
    items = load("equipment.json")["equipped_items"]
    parsed = flatten_equipped_item(items[1])
    assert parsed["slot"] == "TABARD"
    assert parsed["name"] is None
    assert parsed["item_level"] is None
    assert parsed["quality"] is None


def test_flatten_equipped_item_missing_quality_only():
    items = load("equipment.json")["equipped_items"]
    parsed = flatten_equipped_item(items[2])
    assert parsed["slot"] == "MAIN_HAND"
    assert parsed["name"] == "Two-Hander"
    assert parsed["item_level"] == 502
    assert parsed["quality"] is None


def test_extract_profession_tier_uses_latest_tier():
    profs = load("professions.json")["primaries"]
    parsed = extract_profession_tier(profs[0])
    assert parsed == {
        "name": "Blacksmithing",
        "skill_points": 87,
        "max_skill_points": 100,
    }


def test_extract_profession_tier_no_tiers():
    profs = load("professions.json")["primaries"]
    parsed = extract_profession_tier(profs[1])
    assert parsed == {
        "name": "Mining",
        "skill_points": 0,
        "max_skill_points": 0,
    }


def test_extract_profession_tier_secondary():
    profs = load("professions.json")["secondaries"]
    parsed = extract_profession_tier(profs[0])
    assert parsed == {
        "name": "Cooking",
        "skill_points": 25,
        "max_skill_points": 100,
    }
