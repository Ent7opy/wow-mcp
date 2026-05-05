from wow_mcp.app import client, config, mcp, tool_safe
from wow_mcp.parsers import (
    extract_profession_tier,
    extract_profession_with_recipes,
    flatten_equipped_item,
    summarize_achievement_progress,
)


@mcp.tool()
@tool_safe
def get_character_profile(
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Get a WoW character's profile including gear, spec, and item level.

    Args:
        character: Character name (e.g. 'kaelstan'). Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug (e.g. 'silvermoon'). Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    base = f"/profile/wow/character/{r}/{c}"

    profile = client.get(base, "profile", g)
    equipment = client.get(f"{base}/equipment", "profile", g)

    return {
        "name": profile.get("name"),
        "level": profile.get("level"),
        "race": (profile.get("race") or {}).get("name"),
        "class": (profile.get("character_class") or {}).get("name"),
        "active_spec": (profile.get("active_spec") or {}).get("name"),
        "average_item_level": profile.get("average_item_level"),
        "equipped_item_level": profile.get("equipped_item_level"),
        "realm": (profile.get("realm") or {}).get("name"),
        "faction": (profile.get("faction") or {}).get("name"),
        "equipped_items": [flatten_equipped_item(i) for i in equipment.get("equipped_items", [])],
    }


@mcp.tool()
@tool_safe
def get_character_professions(
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
    include_recipes: bool = False,
) -> dict:
    """Get a WoW character's professions with current skill levels.

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
        include_recipes: If True, also return a per-tier breakdown including
            every known_recipe the character has learned (id + name). Default
            False keeps the response small for "what skills do I have?"
            questions; flip to True to answer "what can I craft?" or "what
            recipes am I missing?".
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/professions", "profile", g)

    extract = extract_profession_with_recipes if include_recipes else extract_profession_tier
    return {
        "primaries": [extract(p) for p in data.get("primaries", [])],
        "secondaries": [extract(p) for p in data.get("secondaries", [])],
    }


@mcp.tool()
@tool_safe
def get_character_mounts(
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Get all mounts collected by a WoW character.

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/collections/mounts", "profile", g)

    names = [(m.get("mount") or {}).get("name") for m in data.get("mounts", [])]
    return {
        "total_collected": len(names),
        "mounts": names,
    }


@mcp.tool()
@tool_safe
def get_character_achievements(
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
    include_progress: bool = False,
) -> dict:
    """Get achievements for a WoW character.

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
        include_progress: If True, also include in-progress achievements with
            their criteria progress (e.g. "452/500 honorable kills"). Default
            False keeps the response small for "what have I done?" questions.
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/achievements", "profile", g)
    raw = data.get("achievements", [])

    completed = [
        {
            "id": a.get("id"),
            "name": (a.get("achievement") or {}).get("name"),
            "completed_timestamp": a.get("completed_timestamp"),
        }
        for a in raw
        if a.get("completed_timestamp")
    ]
    result: dict = {
        "total_completed": len(completed),
        "achievements": completed,
    }

    if include_progress:
        in_progress = [
            summary
            for a in raw
            if not a.get("completed_timestamp")
            for summary in [summarize_achievement_progress(a)]
            if summary is not None
        ]
        in_progress.sort(
            key=lambda s: s["criteria_completed"] / s["criteria_total"],
            reverse=True,
        )
        result["in_progress"] = in_progress
        result["total_in_progress"] = len(in_progress)

    return result
