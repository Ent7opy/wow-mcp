import json
from pathlib import Path

from wow_mcp.parsers import (
    flatten_encounter_instance,
    flatten_equipped_item,
    flatten_heirloom,
    flatten_journal_item,
    flatten_pet,
    flatten_reputation,
    flatten_toy,
    extract_profession_tier,
    extract_profession_with_recipes,
    summarize_achievement_progress,
)


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


def test_extract_profession_with_recipes_full_breakdown():
    profs = load("professions.json")["primaries"]
    parsed = extract_profession_with_recipes(profs[0])
    assert parsed["name"] == "Blacksmithing"
    assert parsed["skill_points"] == 87
    assert parsed["max_skill_points"] == 100
    assert len(parsed["tiers"]) == 2
    assert parsed["tiers"][0] == {
        "name": "Classic Blacksmithing",
        "skill_points": 300,
        "max_skill_points": 300,
        "known_recipes": [
            {"id": 2660, "name": "Rough Sharpening Stone"},
            {"id": 3320, "name": "Rough Grinding Stone"},
        ],
    }
    assert parsed["tiers"][1]["known_recipes"] == [
        {"id": 49980, "name": "Charged Bismuth Hammer"},
    ]


def test_extract_profession_with_recipes_no_tiers():
    profs = load("professions.json")["primaries"]
    parsed = extract_profession_with_recipes(profs[1])
    assert parsed == {
        "name": "Mining",
        "skill_points": 0,
        "max_skill_points": 0,
        "tiers": [],
    }


def test_summarize_achievement_progress_multi_step():
    achievements = load("achievements.json")["achievements"]
    hemet = next(a for a in achievements if a["id"] == 941)
    assert summarize_achievement_progress(hemet) == {
        "id": 941,
        "name": "Hemet Nesingwary: The Collected Quests",
        "criteria_completed": 1,
        "criteria_total": 3,
    }


def test_summarize_achievement_progress_single_counter():
    achievements = load("achievements.json")["achievements"]
    kills = next(a for a in achievements if a["id"] == 515)
    assert summarize_achievement_progress(kills) == {
        "id": 515,
        "name": "500 Honorable Kills",
        "criteria_completed": 0,
        "criteria_total": 1,
        "current_amount": 452,
    }


def test_summarize_achievement_progress_untouched_returns_none():
    achievements = load("achievements.json")["achievements"]
    untouched = next(a for a in achievements if a["id"] == 9999)
    assert summarize_achievement_progress(untouched) is None


def test_summarize_achievement_progress_no_criteria_returns_none():
    assert summarize_achievement_progress({"id": 1, "achievement": {"name": "Bare"}}) is None


def test_flatten_encounter_instance_multi_difficulty():
    expansion = load("encounters.json")["expansions"][0]
    instance = expansion["instances"][0]
    parsed = flatten_encounter_instance(instance, expansion["expansion"]["name"])
    assert parsed == {
        "name": "Den of Nalorakk",
        "expansion": "Midnight",
        "difficulties": [
            {
                "difficulty": "Normal",
                "status": "Complete",
                "completed_count": 4,
                "total_count": 4,
            },
            {
                "difficulty": "Heroic",
                "status": "Incomplete",
                "completed_count": 2,
                "total_count": 4,
            },
        ],
    }


def test_flatten_encounter_instance_no_modes():
    parsed = flatten_encounter_instance({"instance": {"name": "Bare"}}, "ExpY")
    assert parsed == {"name": "Bare", "expansion": "ExpY", "difficulties": []}


def test_flatten_journal_item_normal():
    items = load("journal_encounter.json")["items"]
    assert flatten_journal_item(items[0]) == {"id": 159324, "name": "Blood Elder's Bindings"}
    assert flatten_journal_item(items[1]) == {"id": 159330, "name": "Underrot Crawg Reins"}


def test_flatten_journal_item_missing_item_field():
    items = load("journal_encounter.json")["items"]
    assert flatten_journal_item(items[3]) == {"id": None, "name": None}


def test_flatten_heirloom():
    items = load("collections.json")["heirlooms"]["heirlooms"]
    assert flatten_heirloom(items[0]) == {
        "id": 709,
        "name": "Tattered Dreadmist Mask",
        "upgrade_level": 0,
    }
    assert flatten_heirloom(items[1])["upgrade_level"] == 3


def test_flatten_pet():
    items = load("collections.json")["pets"]["pets"]
    assert flatten_pet(items[0]) == {
        "id": 387,
        "name": "Snake",
        "level": 4,
        "quality": "Uncommon",
    }


def test_flatten_toy():
    items = load("collections.json")["toys"]["toys"]
    assert flatten_toy(items[0]) == {"id": 17716, "name": "Snowball"}
    assert flatten_toy(items[1]) == {"id": 35513, "name": "Brewfest Banner"}


def test_flatten_reputation_classic_tier():
    reps = load("reputations.json")["reputations"]
    parsed = flatten_reputation(reps[0])
    assert parsed == {
        "faction_id": 76,
        "faction": "Orgrimmar",
        "standing": "Friendly",
        "value": 571,
        "max": 6000,
        "progress_pct": 10,
        "tier": 4,
    }


def test_flatten_reputation_renown():
    reps = load("reputations.json")["reputations"]
    parsed = flatten_reputation(reps[1])
    assert parsed == {
        "faction_id": 2503,
        "faction": "Maruuk Centaur",
        "standing": "Renown 12",
        "value": 509,
        "max": 2500,
        "progress_pct": 20,
        "renown_level": 12,
    }


def test_flatten_reputation_missing_value_and_max():
    reps = load("reputations.json")["reputations"]
    parsed = flatten_reputation(reps[2])
    assert parsed == {
        "faction_id": 9999,
        "faction": "Edge Case Faction",
        "standing": "Neutral",
        "value": 0,
        "max": 0,
        "progress_pct": 0,
    }
    assert "tier" not in parsed
    assert "renown_level" not in parsed
