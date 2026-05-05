from wow_mcp.app import client, config, mcp, tool_safe
from wow_mcp.parsers import extract_profession_tier, flatten_equipped_item


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
) -> dict:
    """Get a WoW character's professions with current skill levels.

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/professions", "profile", g)

    return {
        "primaries": [extract_profession_tier(p) for p in data.get("primaries", [])],
        "secondaries": [extract_profession_tier(p) for p in data.get("secondaries", [])],
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
) -> dict:
    """Get completed achievements for a WoW character.

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/achievements", "profile", g)

    completed = [
        {
            "id": a.get("id"),
            "name": (a.get("achievement") or {}).get("name"),
            "completed_timestamp": a.get("completed_timestamp"),
        }
        for a in data.get("achievements", [])
        if a.get("completed_timestamp")
    ]
    return {
        "total_completed": len(completed),
        "achievements": completed,
    }
