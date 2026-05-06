# WoW MCP Assistant

A personal MCP server that connects Claude Desktop to the Battle.net API, giving Claude live access to your WoW character data — gear, professions, mounts, achievements, and auction house prices.

---

## Prerequisites

- Python 3.10+
- [Claude Desktop](https://claude.ai/download) installed

---

## 1. Battle.net App Setup

1. Go to [https://develop.battle.net](https://develop.battle.net) and log in
2. Click **Create Client**
3. Fill in a name (e.g. `wow-mcp`), set the redirect URL to `http://localhost:8080/callback`
4. Note your **Client ID** and **Client Secret**

---

## 2. Installation

```bash
git clone https://github.com/YOUR_USERNAME/wow-mcp.git
cd wow-mcp
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in your credentials and character details:

```
BNET_CLIENT_ID=your_client_id_here
BNET_CLIENT_SECRET=your_client_secret_here

WOW_CHARACTER_NAME=yourcharactername
WOW_REALM=your-realm-name
WOW_REGION=eu
```

**Realm name format:** lowercase with hyphens, e.g. `chamber-of-aspects`, `silvermoon`, `twisting-nether`

**Region options:** `eu`, `us`, `kr`, `tw`

---

## 3. Claude Desktop Config

Copy the content of `claude_desktop_config.example.json` into your Claude Desktop config file:

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Update the `args` path to the absolute path of `server.py` on your machine, and fill in your credentials in the `env` block.

**Windows example:**
```json
{
  "mcpServers": {
    "wow-assistant": {
      "command": "python",
      "args": ["C:\\Users\\YourName\\Documents\\wow-mcp\\server.py"],
      "env": {
        "BNET_CLIENT_ID": "your_client_id",
        "BNET_CLIENT_SECRET": "your_client_secret",
        "WOW_CHARACTER_NAME": "yourcharactername",
        "WOW_REALM": "silvermoon",
        "WOW_REGION": "eu"
      }
    }
  }
}
```

Restart Claude Desktop after saving the config. You should see the hammer icon appear in the chat input area, indicating the MCP tools are loaded.

---

## 4. System Prompt (Claude Desktop Settings)

In Claude Desktop → Settings → add this as your system prompt, filling in your character details:

```
You are a WoW assistant for [Character Name], a [Race] [Class] on [Realm].

At the start of each relevant conversation:
- Call get_player_preferences to understand the player's current goals and focus
- Call get_character_profile when gear, spec, or ilvl context is needed

Rules:
- For current Midnight expansion content (zones, NPCs, quests, renown, patch mechanics), use web search — do not rely on training data for anything post-2025
- Tailor all recommendations to the character's actual equipped ilvl, spec, and profession skill levels
- When asked about crafting vs selling, always call get_auction_house_prices and get_character_professions before answering
- For "what can I craft" or "do I have a recipe for X", call get_character_professions with include_recipes=True
- For allied-race unlocks, faction grinds, or any rep-gated goal, call get_character_reputations — a faction absent from the response means the player has not started that questline yet
- For "what does X dungeon/raid drop" or "what dungeon drops Y mount", call get_dungeon_or_raid_loot
- For mount questions, call get_character_mounts to skip mounts already collected; for "what mounts could I chase", call get_missing_mounts with name_filter and (optionally) include_source=True for source category and faction gate
- For "have I done X questline" or "am I currently on Y", call find_character_quests — pairs with get_character_reputations for rep-gated unlocks
- For heirloom, pet, or toy questions, call get_character_collection with the matching kind
- For "how close am I to X achievement", call get_character_achievements with include_progress=True
- For WoW Token gold-price glance questions, call get_wow_token_price
- Keep answers direct and practical — skip generic disclaimers
```

---

## 5. Updating Preferences

Edit `preferences.json` directly whenever your goals or focus changes. Claude reads it fresh on every call — no server restart needed.

```json
{
  "goals": ["mount collecting", "profession economics", "casual PVE"],
  "dislikes": ["hardcore raiding", "PVP"],
  "current_focus": "Hara'ti renown grind",
  "playstyle": "casual, questing and exploring",
  "character_backstory_notes": "Notes about your character for narrative context"
}
```

---

## 6. Tools Reference

| Tool | What it returns |
|------|----------------|
| `get_character_profile` | Name, level, race, class, spec, avg/equipped ilvl, faction, full gear list with slot/name/ilvl/quality |
| `get_character_professions(include_recipes=False)` | Primary and secondary professions with current and max skill points. With `include_recipes=True`, also returns a per-tier breakdown including every known recipe (id + name) |
| `get_character_mounts` | Total collected count and full list of mount names |
| `get_character_achievements(include_progress=False)` | Completed achievements with timestamps. With `include_progress=True`, also returns an `in_progress` list sorted by completion ratio (e.g. "15/16 — one step from done") |
| `get_character_reputations` | Faction standings — classic tier or renown level, value/max within current tier, derived `progress_pct`. Factions never met don't appear, which is itself a useful signal for unlock questions |
| `get_character_collection(kind)` | `kind` is one of `'heirlooms'`, `'pets'`, `'toys'`. Uniform `{kind, total, items}` shape with per-kind identifying fields (upgrade_level for heirlooms, level/quality for pets) |
| `find_character_quests(query, limit=30)` | Substring search across both completed and in-progress quest lists; returns matched quests in each category with id+name. Pairs with `get_character_reputations` for rep-gated unlock checks |
| `get_auction_house_prices(item_name)` | Total listings, cheapest price in gold, top 20 cheapest listings |
| `get_dungeon_or_raid_loot(name)` | Case-insensitive substring search on the journal-instance index, then walks each encounter for its loot table (id + name per item). Returns `ambiguous: True` with candidates when the name matches multiple instances |
| `get_missing_mounts(name_filter=None, limit=30, include_source=False)` | Diff of the mount index against the character's collected list, alphabetised, filtered, and capped. With `include_source=True`, parallel-fetches each returned mount's detail and attaches `source_type` (DROP/VENDOR/QUEST/ACHIEVEMENT/etc.) and `faction_required` |
| `get_wow_token_price(region=None)` | Current WoW Token price in gold for the region, plus last-updated timestamp and seconds-since-update for freshness |
| `get_player_preferences` | Your goals, dislikes, current focus, and playstyle from `preferences.json` |

---

## Troubleshooting

- **Tools not appearing in Claude Desktop:** double-check the absolute path in `args` and restart Claude Desktop
- **`401 Unauthorized`:** verify your Client ID and Secret are correct and the Battle.net app is active
- **`404` on character endpoints:** confirm `WOW_CHARACTER_NAME` and `WOW_REALM` are lowercase with hyphens
- **Empty auction results:** try a more specific item name matching the exact in-game name (e.g. `Midnight Ore` not `ore`)
