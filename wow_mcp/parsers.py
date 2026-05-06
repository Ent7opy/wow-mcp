def flatten_equipped_item(raw: dict) -> dict:
    return {
        "slot": (raw.get("slot") or {}).get("type"),
        "name": raw.get("name") or (raw.get("item") or {}).get("name"),
        "item_level": (raw.get("level") or {}).get("value"),
        "quality": (raw.get("quality") or {}).get("type"),
    }


def flatten_encounter_instance(raw: dict, expansion_name: str | None) -> dict:
    """Flatten one entry from /encounters/{dungeons,raids}.expansions[].instances[]
    into {name, expansion, difficulties: [{difficulty, status, completed_count,
    total_count}]} — the shape Claude wants for "have I cleared X?" answers.

    Each instance can have multiple difficulty modes (Normal, Heroic, Mythic);
    the API returns a separate `modes` entry per difficulty the character has
    touched. Status comes back as 'COMPLETE' or 'INCOMPLETE'."""
    return {
        "name": (raw.get("instance") or {}).get("name"),
        "expansion": expansion_name,
        "difficulties": [
            {
                "difficulty": (mode.get("difficulty") or {}).get("name"),
                "status": (mode.get("status") or {}).get("name"),
                "completed_count": (mode.get("progress") or {}).get("completed_count"),
                "total_count": (mode.get("progress") or {}).get("total_count"),
            }
            for mode in raw.get("modes", [])
        ],
    }


def flatten_journal_item(raw: dict) -> dict:
    """Flatten one entry from journal-encounter.items[].

    Each entry wraps the actual item under `.item`; missing or unparented
    entries (rare but possible in older data) collapse to {id: None,
    name: None} rather than raising."""
    item = raw.get("item") or {}
    return {"id": item.get("id"), "name": item.get("name")}


def flatten_heirloom(raw: dict) -> dict:
    return {
        "id": (raw.get("heirloom") or {}).get("id"),
        "name": (raw.get("heirloom") or {}).get("name"),
        "upgrade_level": (raw.get("upgrade") or {}).get("level", 0),
    }


def flatten_pet(raw: dict) -> dict:
    return {
        "id": (raw.get("species") or {}).get("id"),
        "name": (raw.get("species") or {}).get("name"),
        "level": raw.get("level"),
        "quality": (raw.get("quality") or {}).get("name"),
    }


def flatten_toy(raw: dict) -> dict:
    return {
        "id": (raw.get("toy") or {}).get("id"),
        "name": (raw.get("toy") or {}).get("name"),
    }


def flatten_reputation(raw: dict) -> dict:
    """Reduce a raw reputation entry to {faction, standing, value/max, pct}.

    Two API shapes coexist: classic factions carry an integer `tier` (1-8 for
    Hated through Exalted), while renown-style factions (Dragonflight onward)
    carry `renown_level` instead. The fields are surfaced only when present so
    Claude can distinguish them downstream."""
    faction = raw.get("faction") or {}
    standing = raw.get("standing") or {}
    value = standing.get("value", 0) or 0
    max_value = standing.get("max", 0) or 0
    progress_pct = round(100 * value / max_value) if max_value else 0

    result = {
        "faction_id": faction.get("id"),
        "faction": faction.get("name"),
        "standing": standing.get("name"),
        "value": value,
        "max": max_value,
        "progress_pct": progress_pct,
    }
    if "tier" in standing:
        result["tier"] = standing["tier"]
    if "renown_level" in standing:
        result["renown_level"] = standing["renown_level"]
    return result


def summarize_achievement_progress(raw: dict) -> dict | None:
    """Reduce a raw achievement entry to its in-progress shape, or None if there
    is no useful progress signal to surface.

    Only meaningful for *incomplete* achievements — callers should filter on
    completed_timestamp before calling. Old completed achievements often have
    stale criteria flags (all false), so criteria are not authoritative for
    completion."""
    criteria = raw.get("criteria") or {}
    children = criteria.get("child_criteria") or []
    name = (raw.get("achievement") or {}).get("name")
    achievement_id = raw.get("id")

    if children:
        completed = sum(1 for c in children if c.get("is_completed"))
        total = len(children)
        amount = children[0].get("amount") if total == 1 else None
        if completed == 0 and not amount:
            return None
        result = {
            "id": achievement_id,
            "name": name,
            "criteria_completed": completed,
            "criteria_total": total,
        }
        if amount:
            result["current_amount"] = amount
        return result

    return None


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


def extract_profession_with_recipes(profession: dict) -> dict:
    """Same as extract_profession_tier but also includes a per-tier breakdown
    with the known_recipes the API already returns. The top-level summary
    fields stay identical to extract_profession_tier so include_recipes=True
    is purely additive."""
    summary = extract_profession_tier(profession)
    summary["tiers"] = [
        {
            "name": (t.get("tier") or {}).get("name"),
            "skill_points": t.get("skill_points", 0),
            "max_skill_points": t.get("max_skill_points", 0),
            "known_recipes": [
                {"id": r.get("id"), "name": r.get("name")}
                for r in (t.get("known_recipes") or [])
            ],
        }
        for t in profession.get("tiers", [])
    ]
    return summary
