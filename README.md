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
- Keep answers direct and practical — skip generic disclaimers
- For mount questions, call get_character_mounts to skip mounts already collected
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
| `get_character_professions` | Primary and secondary professions with current and max skill points |
| `get_character_mounts` | Total collected count and full list of mount names |
| `get_character_achievements` | Total completed count and list of achievements with timestamps |
| `get_auction_house_prices(item_name)` | Total listings, cheapest price in gold, top 20 cheapest listings |
| `get_player_preferences` | Your goals, dislikes, current focus, and playstyle from `preferences.json` |

---

## Troubleshooting

- **Tools not appearing in Claude Desktop:** double-check the absolute path in `args` and restart Claude Desktop
- **`401 Unauthorized`:** verify your Client ID and Secret are correct and the Battle.net app is active
- **`404` on character endpoints:** confirm `WOW_CHARACTER_NAME` and `WOW_REALM` are lowercase with hyphens
- **Empty auction results:** try a more specific item name matching the exact in-game name (e.g. `Midnight Ore` not `ore`)
