def flatten_equipped_item(raw: dict) -> dict:
    return {
        "slot": (raw.get("slot") or {}).get("type"),
        "name": raw.get("name") or (raw.get("item") or {}).get("name"),
        "item_level": (raw.get("level") or {}).get("value"),
        "quality": (raw.get("quality") or {}).get("type"),
    }


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
