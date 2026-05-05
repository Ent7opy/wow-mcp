import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

CLIENT_ID = os.environ["BNET_CLIENT_ID"]
CLIENT_SECRET = os.environ["BNET_CLIENT_SECRET"]

DEFAULT_CHARACTER = os.getenv("WOW_CHARACTER_NAME", "").lower()
DEFAULT_REALM = os.getenv("WOW_REALM", "").lower()
DEFAULT_REGION = os.getenv("WOW_REGION", "eu").lower()

mcp = FastMCP("wow-assistant")


def get_access_token(region: str) -> str:
    resp = httpx.post(
        f"https://{region}.battle.net/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def bnet_get(path: str, namespace: str, token: str, region: str) -> dict:
    resp = httpx.get(
        f"https://{region}.api.blizzard.com{path}",
        params={"namespace": f"{namespace}-{region}", "locale": "en_US"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


def resolve(character: str | None, realm: str | None, region: str | None) -> tuple[str, str, str]:
    c = (character or DEFAULT_CHARACTER).lower()
    r = (realm or DEFAULT_REALM).lower()
    g = (region or DEFAULT_REGION).lower()
    if not c or not r:
        raise ValueError("character and realm are required — pass them as arguments or set WOW_CHARACTER_NAME / WOW_REALM in .env")
    return c, r, g


@mcp.tool()
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
    try:
        c, r, g = resolve(character, realm, region)
        token = get_access_token(g)
        base = f"/profile/wow/character/{r}/{c}"

        profile = bnet_get(base, "profile", token, g)
        equipment = bnet_get(f"{base}/equipment", "profile", token, g)

        equipped_items = [
            {
                "slot": item["slot"]["type"],
                "name": item["item"]["name"],
                "item_level": item.get("level", {}).get("value"),
                "quality": item.get("quality", {}).get("type"),
            }
            for item in equipment.get("equipped_items", [])
        ]

        return {
            "name": profile.get("name"),
            "level": profile.get("level"),
            "race": profile.get("race", {}).get("name"),
            "class": profile.get("character_class", {}).get("name"),
            "active_spec": profile.get("active_spec", {}).get("name"),
            "average_item_level": profile.get("average_item_level"),
            "equipped_item_level": profile.get("equipped_item_level"),
            "realm": profile.get("realm", {}).get("name"),
            "faction": profile.get("faction", {}).get("name"),
            "equipped_items": equipped_items,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
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
    try:
        c, r, g = resolve(character, realm, region)
        token = get_access_token(g)
        data = bnet_get(
            f"/profile/wow/character/{r}/{c}/professions",
            "profile",
            token,
            g,
        )

        def extract(profs):
            result = []
            for p in profs:
                tiers = p.get("tiers", [])
                if tiers:
                    latest = tiers[-1]
                    skill = latest.get("skill_points", 0)
                    max_skill = latest.get("max_skill_points", 0)
                else:
                    skill = 0
                    max_skill = 0
                result.append({
                    "name": p.get("profession", {}).get("name"),
                    "skill_points": skill,
                    "max_skill_points": max_skill,
                })
            return result

        return {
            "primaries": extract(data.get("primaries", [])),
            "secondaries": extract(data.get("secondaries", [])),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
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
    try:
        c, r, g = resolve(character, realm, region)
        token = get_access_token(g)
        data = bnet_get(
            f"/profile/wow/character/{r}/{c}/collections/mounts",
            "profile",
            token,
            g,
        )

        mounts = data.get("mounts", [])
        names = [m.get("mount", {}).get("name") for m in mounts]

        return {
            "total_collected": len(names),
            "mounts": names,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
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
    try:
        c, r, g = resolve(character, realm, region)
        token = get_access_token(g)
        data = bnet_get(
            f"/profile/wow/character/{r}/{c}/achievements",
            "profile",
            token,
            g,
        )

        completed = [
            {
                "id": a.get("id"),
                "name": a.get("achievement", {}).get("name"),
                "completed_timestamp": a.get("completed_timestamp"),
            }
            for a in data.get("achievements", [])
            if a.get("completed_timestamp")
        ]

        return {
            "total_completed": len(completed),
            "achievements": completed,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
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
    try:
        _, r, g = resolve("_", realm, region)
        token = get_access_token(g)

        realm_data = bnet_get(f"/data/wow/realm/{r}", "dynamic", token, g)
        href = realm_data.get("connected_realm", {}).get("href", "")
        connected_realm_id = href.split("/connected-realm/")[1].split("?")[0]

        auctions_data = bnet_get(
            f"/data/wow/connected-realm/{connected_realm_id}/auctions",
            "dynamic",
            token,
            g,
        )

        search_resp = httpx.get(
            f"https://{g}.api.blizzard.com/data/wow/search/item",
            params={
                "namespace": f"static-{g}",
                "locale": "en_US",
                "name.en_US": item_name,
                "_pageSize": 10,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        matching_ids = {r["data"]["id"] for r in search_data.get("results", [])}

        if not matching_ids:
            return {"error": f"No items found matching '{item_name}'"}

        listings = []
        for auction in auctions_data.get("auctions", []):
            if auction.get("item", {}).get("id") in matching_ids:
                buyout = auction.get("buyout", 0)
                unit_price = auction.get("unit_price", 0)
                price_copper = buyout or unit_price
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
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_player_preferences() -> dict:
    """Read the player's preferences, goals, and current focus from preferences.json."""
    prefs_path = Path(__file__).parent / "preferences.json"
    if not prefs_path.exists():
        return {
            "note": (
                "preferences.json not found. Create it next to server.py with keys: "
                "goals, dislikes, current_focus, playstyle, character_backstory_notes"
            )
        }
    try:
        return json.loads(prefs_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
