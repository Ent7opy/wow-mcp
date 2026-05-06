import time
from datetime import datetime, timezone

from wow_mcp.app import client, config, mcp, tool_safe
from wow_mcp.parsers import flatten_journal_item


CONNECTED_REALM_CACHE_TTL = 86400
JOURNAL_CACHE_TTL = 86400
MOUNT_INDEX_CACHE_TTL = 86400


@mcp.tool()
@tool_safe
def get_auction_house_prices(
    item_name: str,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """Get current auction house prices for a named item.

    Args:
        item_name: Exact or partial item name to search for (e.g. 'Midnight Ore').
        realm: Realm slug to check AH on. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    _, r, g = config.resolve("_", realm, region)

    realm_data = client.get(f"/data/wow/realm/{r}", "dynamic", g, cache_ttl=CONNECTED_REALM_CACHE_TTL)
    href = ((realm_data.get("connected_realm") or {}).get("href")) or ""
    connected_realm_id = href.split("/connected-realm/")[1].split("?")[0]

    auctions_data = client.get(
        f"/data/wow/connected-realm/{connected_realm_id}/auctions",
        "dynamic",
        g,
    )

    search_data = client.get(
        "/data/wow/search/item",
        "static",
        g,
        params={"name.en_US": item_name, "_pageSize": 10},
    )
    matching_ids = {result["data"]["id"] for result in search_data.get("results", [])}
    if not matching_ids:
        return {"error": f"No items found matching '{item_name}'"}

    listings = []
    for auction in auctions_data.get("auctions", []):
        if (auction.get("item") or {}).get("id") in matching_ids:
            price_copper = auction.get("buyout") or auction.get("unit_price") or 0
            if price_copper:
                listings.append({
                    "quantity": auction.get("quantity", 1),
                    "price_gold": round(price_copper / 10000, 2),
                })

    listings.sort(key=lambda x: x["price_gold"])

    return {
        "item_name": item_name,
        "total_listings": len(listings),
        "cheapest_gold": listings[0]["price_gold"] if listings else None,
        "top_20_cheapest": listings[:20],
    }


@mcp.tool()
@tool_safe
def get_wow_token_price(region: str | None = None) -> dict:
    """Get the current WoW Token price in gold for a given region.

    The token is a Blizzard-issued in-game item that converts to game time
    or Battle.net balance. Its gold price is set by the game's own market
    and updates roughly every 20 minutes. Casual flavor question Claude
    might field a few times a week ("is the token cheap right now?").

    Args:
        region: Region code — eu, us, kr, tw. Falls back to WOW_REGION
            env var (defaults to 'eu'). Token price is region-specific.

    The endpoint exposes only the current snapshot — no historical data is
    available, so Claude shouldn't claim a "trend" without external context.
    """
    _, _, g = config.resolve("_", "_", region)
    data = client.get("/data/wow/token/index", "dynamic", g)

    price_copper = data.get("price", 0)
    last_updated_ms = data.get("last_updated_timestamp", 0)
    last_updated_dt = datetime.fromtimestamp(last_updated_ms / 1000, tz=timezone.utc)

    return {
        "region": g,
        "price_gold": price_copper // 10000,
        "last_updated": last_updated_dt.isoformat(),
        "seconds_since_update": int(time.time() - last_updated_ms / 1000),
    }


@mcp.tool()
@tool_safe
def get_dungeon_or_raid_loot(name: str, region: str | None = None) -> dict:
    """Look up the loot table for a dungeon or raid by name.

    Walks the journal-instance index, finds the matching instance, then
    returns each encounter's loot list (item id + name). All three
    underlying endpoints are static-namespace and cached for 24h, so
    repeat queries on the same instance are nearly free.

    Args:
        name: Dungeon or raid name. Case-insensitive substring match —
            "underrot" matches "The Underrot". If multiple match and none
            is exact, returns an `ambiguous: True` response with the top
            matches so the caller can disambiguate.
        region: Region code — eu, us, kr, tw. Falls back to WOW_REGION
            env var. Static-namespace data is region-keyed but content is
            identical across regions; pick the configured one.
    """
    _, _, g = config.resolve("_", "_", region)

    index = client.get(
        "/data/wow/journal-instance/index", "static", g, cache_ttl=JOURNAL_CACHE_TTL
    )
    needle = name.strip().lower()
    matches = [
        i for i in index.get("instances", [])
        if needle in (i.get("name") or "").lower()
    ]
    if not matches:
        return {"error": f"No dungeon or raid found matching {name!r}"}

    exact = [m for m in matches if (m.get("name") or "").lower() == needle]
    if exact:
        chosen = exact[0]
    elif len(matches) == 1:
        chosen = matches[0]
    else:
        return {
            "ambiguous": True,
            "query": name,
            "matches": [{"id": m.get("id"), "name": m.get("name")} for m in matches[:10]],
            "note": "Multiple matches — call again with a more specific name.",
        }

    instance = client.get(
        f"/data/wow/journal-instance/{chosen['id']}",
        "static",
        g,
        cache_ttl=JOURNAL_CACHE_TTL,
    )

    encounters = []
    for enc_ref in instance.get("encounters", []):
        encounter = client.get(
            f"/data/wow/journal-encounter/{enc_ref['id']}",
            "static",
            g,
            cache_ttl=JOURNAL_CACHE_TTL,
        )
        encounters.append({
            "name": encounter.get("name"),
            "items": [flatten_journal_item(i) for i in encounter.get("items", [])],
        })

    return {
        "name": instance.get("name"),
        "expansion": (instance.get("expansion") or {}).get("name"),
        "category": (instance.get("category") or {}).get("type"),
        "minimum_level": instance.get("minimum_level"),
        "total_encounters": len(encounters),
        "encounters": encounters,
    }


@mcp.tool()
@tool_safe
def get_missing_mounts(
    name_filter: str | None = None,
    limit: int = 30,
    include_source: bool = False,
    character: str | None = None,
    realm: str | None = None,
    region: str | None = None,
) -> dict:
    """List mounts the character has NOT yet collected.

    The mount index has 1500+ entries, so unfiltered queries cap at `limit`
    results (default 30). Always pass a `name_filter` for targeted hunts —
    e.g. name_filter='wolf' to find every uncollected wolf-themed mount.

    With include_source=True, each returned mount is enriched with its
    source category (DROP/VENDOR/QUEST/ACHIEVEMENT/etc.) and faction gate
    if any. That triggers one extra API call per returned mount (cached
    24h, fan-out parallelised), so keep `limit` modest when using it —
    25-30 is a good ceiling.

    Args:
        name_filter: Optional case-insensitive substring filter on mount name.
        limit: Max mounts returned (default 30; pass higher to widen).
        include_source: If True, also fetch and attach source_type, source,
            and faction_required for each returned mount.
        character: Character name. Falls back to WOW_CHARACTER_NAME env var.
        realm: Realm slug. Falls back to WOW_REALM env var.
        region: Region code — eu, us, kr, tw. Defaults to 'eu'.
    """
    c, r, g = config.resolve(character, realm, region)

    index = client.get(
        "/data/wow/mount/index", "static", g, cache_ttl=MOUNT_INDEX_CACHE_TTL
    )
    collected = client.get(
        f"/profile/wow/character/{r}/{c}/collections/mounts", "profile", g
    )

    collected_ids = {
        (m.get("mount") or {}).get("id") for m in collected.get("mounts", [])
    }
    all_mounts = index.get("mounts", [])
    missing = [m for m in all_mounts if m.get("id") not in collected_ids]
    total_missing = len(missing)

    matched = missing
    if name_filter:
        needle = name_filter.lower()
        matched = [m for m in missing if needle in (m.get("name") or "").lower()]

    matched.sort(key=lambda m: (m.get("name") or "").lower())
    returned = [{"id": m.get("id"), "name": m.get("name")} for m in matched[:limit]]

    if include_source and returned:
        specs = [
            {
                "path": f"/data/wow/mount/{m['id']}",
                "namespace": "static",
                "region": g,
                "cache_ttl": MOUNT_INDEX_CACHE_TTL,
            }
            for m in returned
        ]
        details = client.get_many(specs)
        for mount_dict, detail in zip(returned, details):
            source = detail.get("source") or {}
            mount_dict["source_type"] = source.get("type")
            mount_dict["source"] = source.get("name")
            faction = ((detail.get("requirements") or {}).get("faction") or {}).get("name")
            if faction:
                mount_dict["faction_required"] = faction

    return {
        "total_collected": len(collected_ids),
        "total_missing": total_missing,
        "name_filter": name_filter,
        "matched": len(matched) if name_filter else total_missing,
        "truncated": len(matched) > limit,
        "mounts": returned,
    }
