# wow-mcp

A personal MCP server that gives Claude Desktop live access to one player's World of Warcraft data via the Battle.net API. Single-user, local-only, run by Python over stdio. Not a product.

## Target user

A casual WoW player — solo questing, exploration, lore, light crafting, mount/pet collecting. Not a raider, not a Mythic+ runner, not a PvPer. Tools should answer questions the player would actually ask Claude mid-session (e.g. "how close am I to unlocking Vulpera?", "what does this dungeon drop?"), not surface raw stats.

The active player profile lives in [preferences.json](preferences.json) and is read at runtime by `get_player_preferences`. Treat it as authoritative when picking what to recommend.

## Hard constraints

- **No async until a feature needs it.** FastMCP runs sync tools fine. Add `asyncio` only when fan-out volume forces it (the planned missing-mounts tool is the trigger).
- **No Pydantic / response models.** Tools return plain `dict`s; FastMCP serializes them. Adding models for every Blizzard payload is friction every time the API shape shifts.
- **No DI framework / `register()` indirection.** `mcp`, `client`, `config` are module-level singletons in [wow_mcp/app.py](wow_mcp/app.py). Tool modules import them and decorate at import time. Tools register as a side effect of `from wow_mcp.tools import ...` in [server.py](server.py).
- **No custom error hierarchy.** `tool_safe` in [wow_mcp/app.py](wow_mcp/app.py) catches `httpx.HTTPStatusError`, `ValueError`, and the generic fallback. Don't add `BnetNotFound` / `BnetAuthError` subclasses.
- **No external storage.** In-memory caches only. No Redis, no SQLite, no on-disk JSON cache. Process restart wipes them; that's fine.
- **Client-credentials OAuth only.** No interactive user-OAuth flow. This means `/profile/user/wow` (account-wide collections across alts) is unreachable. Don't build features that assume cross-alt data.
- **No Wowhead, no paid third-party APIs, no RAG/embeddings.** Battle.net API is the only data source.
- **Skip anti-goal tools.** Mythic keystone profile, PvP summary, raid log analysis — out of scope for this player.

## Layout

```
server.py                        # 5-line entrypoint: imports tools, mcp.run()
preferences.json                 # the player's goals/dislikes/focus — runtime input
wow_mcp/
  app.py                         # mcp, client, config singletons + tool_safe decorator
  config.py                      # Config dataclass, load_config(), resolve()
  bnet.py                        # BnetClient: pooled httpx, token cache, TTL cache
  parsers.py                     # pure functions: flatten_equipped_item, extract_profession_tier
  tools/
    character.py                 # /profile/wow/character/* tools
    gamedata.py                  # /data/wow/* tools
    local.py                     # file-backed tools (preferences)
tests/
  fixtures/*.json                # captured Blizzard payloads
  test_parsers.py                # pure-function tests, no network
```

## Conventions

### Adding a tool

Pick the file by the API surface it hits, not by feature theme:
- Anything under `/profile/wow/character/{realm}/{char}/...` → [tools/character.py](wow_mcp/tools/character.py)
- Anything under `/data/wow/...` → [tools/gamedata.py](wow_mcp/tools/gamedata.py)
- Anything file-backed → [tools/local.py](wow_mcp/tools/local.py)

Don't pre-split into `economy.py` / `journal.py` / etc. Split a file the day it crosses ~400 lines, not before.

Every tool stacks decorators in this order:
```python
@mcp.tool()
@tool_safe
def my_tool(...) -> dict:
    """Docstring is user-facing — it's what FastMCP shows the model."""
    ...
```

For character-scoped tools, signature is always `character: str | None = None, realm: str | None = None, region: str | None = None` and the body starts with `c, r, g = config.resolve(character, realm, region)`. This keeps the system-prompt-driven default-character flow working.

### Hitting the Battle.net API

Always go through `client.get(path, namespace, region, params=..., cache_ttl=...)`. Never call `httpx` directly from a tool — that path was removed for a reason (the auction tool used to do it and broke the single-error-handling contract).

Three namespaces:
- `static-{region}` — patch-stable content (items, mounts, journal entries, recipes). Safe to cache long: pass `cache_ttl=86400` when the value won't change between patches.
- `dynamic-{region}` — auctions, realms, WoW Token. Auctions update hourly — never cache. Realm metadata effectively never changes — safe to cache.
- `profile-{region}` — character data. Never cache. The player just looted something; stale data is wrong data.

Token caching is automatic — every region gets one cached token with a 5-minute refresh buffer. Don't manage tokens yourself.

### Parsers

Anything that reshapes a Blizzard response into a tool's output dict belongs in [wow_mcp/parsers.py](wow_mcp/parsers.py) as a pure function. Why: Blizzard payloads are inconsistently populated (slots without `level`, professions without `tiers`), parsing has bugs, and pure functions are testable without mocking httpx. The defensive `(x.get("y") or {}).get("z")` chain in `flatten_equipped_item` exists because `level` and `quality` are missing on some slots — don't simplify it.

### Tests

Only pure-function tests, only fixture-based, no network mocking. Add a fixture to `tests/fixtures/` (real captured payload preferred over hand-written) and a test in [test_parsers.py](tests/test_parsers.py). Run with `python -m pytest tests/`. Add `pytest` via `requirements-dev.txt`, not `requirements.txt`.

If a tool's output shape regresses, the fix is to add a fixture covering the broken case and a test pinning the parsed result — not to add try/except.

### Errors

`tool_safe` returns one of these on failure:
- `{"error": "battle.net 404: ...", "status_code": 404}` for HTTP errors
- `{"error": "..."}` for `ValueError` (e.g. unresolved character/realm) and other exceptions

Don't add per-tool try/except. Don't return `traceback`. Don't introduce error subclasses.

### Preferences

Read via `get_player_preferences` (the tool) or `config.preferences_path` (in code). Never `Path(__file__).parent / "preferences.json"` — that path moved when the package was created.

## Verification before shipping a change

1. `python -m pytest tests/` passes.
2. `python -c "import server"` imports without error (registers all tools as a side effect).
3. For new tools touching the Battle.net API, smoke-test once against the real character (Kaelstan / azjolnerub / eu) and confirm the output dict shape is what you'd want Claude to read aloud.
4. If you added a fan-out tool (>5 calls per invocation), confirm the second invocation is faster than the first — it should hit the token cache and any `cache_ttl` entries.
