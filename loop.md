You are working on `wow-mcp` — a personal MCP server connecting Claude Desktop to the Battle.net API for one casual WoW player. Each iteration of this loop ships one concrete, atomic improvement.

## What to do this iteration

1. **Re-orient.** Read [CLAUDE.md](CLAUDE.md) to refresh on goals, constraints, conventions, and the verification checklist. Read [preferences.json](preferences.json) to confirm the player's current focus — if it's shifted, weigh that over the priority order below.

2. **Check the tree.** Run `git status` and `git log --oneline -5`.
   - If there's uncommitted work-in-progress: finish it, verify it, commit it. Don't start anything new.
   - If the tree is clean: pick the next thing.

3. **Pick one increment.** Order of preference:
   - **Free wins** — data the existing tools already fetch but discard. The `/achievements` endpoint returns per-criterion progress; the `/professions` endpoint returns `known_recipes` per tier. Surfacing either of those is a refactor, not a new endpoint call.
   - **Single-call profile features** — reputations, statistics, completed encounters, completed-quest lookup. One Battle.net call, no fan-out.
   - **Game-data tools serving stated goals** (mount collecting, profession economics, allied-race progression): WoW Token price, dungeon/raid loot journal, missing-mounts diff, pet/toy/heirloom collections.
   - **Skip anti-goals**: Mythic+, PvP, raid logs, hunter pets, anything requiring user-OAuth.

   Resist scope creep. "While I'm in here" refactors are forbidden — they make the iteration unreviewable.

4. **Implement the smallest viable version.** Tool placement and decorator pattern per CLAUDE.md (`@mcp.tool()` then `@tool_safe`, in `tools/{character,gamedata,local}.py` chosen by API surface). Use `client.get(...)`. If parsing is non-trivial, put it in [wow_mcp/parsers.py](wow_mcp/parsers.py) and add a fixture-based test.

5. **Verify.** Run the CLAUDE.md checklist:
   - `python -m pytest tests/` passes
   - `python -c "import server"` succeeds
   - For new API-touching tools: smoke-test against the real character (`character='kaelstan', realm='azjolnerub', region='eu'`) and confirm the output is something Claude could read aloud, not a JSON dump

6. **Commit and push.** One commit, scope-tight message describing what was added (e.g. `Add get_character_reputations tool`). Push to `origin/master` after the commit lands. Don't open a PR — direct-to-master is fine for this personal repo.

7. **Report.** End with a one-paragraph summary: what you built, what verification ran, anything the user should know before the next iteration fires.

## Hard rules

- Honour every constraint in [CLAUDE.md](CLAUDE.md). No async, no Pydantic, no DI, no error subclasses, no external storage, no Wowhead, no anti-goal tools.
- Tool names and signatures, once added, are stable contracts. Don't rename or reshape existing tools.
- One increment per iteration. If you can't finish in one pass, leave the tree dirty — the next iteration finishes and commits.
- Push the iteration's commit to `origin/master` directly. Don't open a PR. Never `--no-verify`.
- Never force-push. If `git push` is rejected (someone else pushed in the meantime), pull with rebase and try again — don't override.
- Never modify `preferences.json` — that's user-owned state.

## When there's nothing left to do

If you've audited the unbuilt-tool space and concluded everything reasonable is built (or actively in flight elsewhere), say so explicitly and stop. Do not invent busywork — no speculative refactors, no new abstractions, no docs nobody asked for.
