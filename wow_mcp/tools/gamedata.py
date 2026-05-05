from wow_mcp.app import client, config, mcp, tool_safe


CONNECTED_REALM_CACHE_TTL = 86400


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
