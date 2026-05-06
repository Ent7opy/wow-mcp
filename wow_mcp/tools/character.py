from wow_mcp.app import client, config, mcp, tool_safe
from wow_mcp.parsers import (
    extract_profession_tier,
    extract_profession_with_recipes,
    flatten_equipped_item,
    flatten_heirloom,
    flatten_pet,
    flatten_reputation,
    flatten_toy,
    summarize_achievement_progress,
)


_COLLECTION_PARSERS = {
    "heirlooms": flatten_heirloom,
    "pets": flatten_pet,
    "toys": flatten_toy,
}


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


@mcp.tool()
@tool_safe
def get_character_reputations(
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Get a WoW character's reputation standings with every faction they've
    interacted with — classic factions (tier-based) and renown factions
    (Dragonflight onward) both included.

    Factions the character has never met do not appear in the response. So if
    a player is asking about an allied-race or rep-gated unlock and the
    relevant faction is missing, the answer is "you haven't started that
    questline yet" rather than "you're at zero rep".

    Args:
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    data = client.get(f"/profile/wow/character/{r}/{c}/reputations", "profile", g)

    reputations = [flatten_reputation(rep) for rep in data.get("reputations", [])]
    return {
        "total": len(reputations),
        "reputations": reputations,
    }


@mcp.tool()
@tool_safe
def get_character_collection(
    kind: str,
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Get one of the character's non-mount collections: heirlooms, pets, or toys.

    Mounts have their own dedicated tool (get_character_mounts) since they're
    the most-asked-about collection. This tool covers the others.

    Args:
        kind: One of 'heirlooms', 'pets', 'toys'. Required.
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.

    Returns a uniform shape: {kind, total, items}. Each item carries the
    minimum identifying fields for that collection — id and name always,
    plus upgrade_level for heirlooms, level/quality for pets.
    """
    parser = _COLLECTION_PARSERS.get(kind)
    if parser is None:
        raise ValueError(
            f"kind must be one of {sorted(_COLLECTION_PARSERS)} (got {kind!r})"
        )
    c, r, g = config.resolve(character, realm, region)
    data = client.get(
        f"/profile/wow/character/{r}/{c}/collections/{kind}", "profile", g
    )
    items = [parser(entry) for entry in data.get(kind, [])]
    return {
        "kind": kind,
        "total": len(items),
        "items": items,
    }


@mcp.tool()
@tool_safe
def find_character_quests(
    query: str,
    limit: int = 30,
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Find quests matching a name substring across BOTH completed and
    in-progress lists for a character.

    Answers "have I done X?" and "am I currently on X?" in one call. Two
    profile endpoints are fetched in parallel via BnetClient.get_many —
    /quests/completed for the done list and /quests for the active list.
    Both endpoints inline the quest name on each entry, so there's no
    name-to-id resolution needed.

    Pairs naturally with get_character_reputations for rep-gated unlock
    questions: e.g. for the Vulpera unlock, query='Voldunai' or
    query="Vol'dun" surfaces every related quest the character has touched.

    Args:
        query: Case-insensitive substring to match against quest names.
        limit: Cap on each of the two returned lists (default 30).
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)
    base = f"/profile/wow/character/{r}/{c}"
    completed_data, active_data = client.get_many([
        {"path": f"{base}/quests/completed", "namespace": "profile", "region": g},
        {"path": f"{base}/quests", "namespace": "profile", "region": g},
    ])

    needle = query.strip().lower()

    def _matches(entries: list) -> list:
        return [
            {"id": q.get("id"), "name": q.get("name")}
            for q in entries
            if needle in (q.get("name") or "").lower()
        ]

    completed_all = completed_data.get("quests", []) or []
    in_progress_all = active_data.get("in_progress", []) or []
    completed_matches = _matches(completed_all)
    in_progress_matches = _matches(in_progress_all)

    return {
        "query": query,
        "total_completed": len(completed_all),
        "total_in_progress": len(in_progress_all),
        "completed_matches": completed_matches[:limit],
        "completed_match_count": len(completed_matches),
        "in_progress_matches": in_progress_matches[:limit],
        "in_progress_match_count": len(in_progress_matches),
    }
