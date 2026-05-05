def flatten_equipped_item(raw: dict) -> dict:
    return {
        "slot": (raw.get("slot") or {}).get("type"),
        "name": raw.get("name") or (raw.get("item") or {}).get("name"),
        "item_level": (raw.get("level") or {}).get("value"),
        "quality": (raw.get("quality") or {}).get("type"),
    }


def extract_profession_tier(profession: dict) -> dict:
    tiers = profession.get("tiers", [])
    if tiers:
        latest = tiers[-1]
        skill = latest.get("skill_points", 0)
        max_skill = latest.get("max_skill_points", 0)
    else:
        skill = 0
        max_skill = 0
    return {
        "name": (profession.get("profession") or {}).get("name"),
        "skill_points": skill,
        "max_skill_points": max_skill,
    }
