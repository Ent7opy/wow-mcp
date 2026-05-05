import json

from wow_mcp.app import config, mcp, tool_safe


@mcp.tool()
@tool_safe
def get_player_preferences() -> dict:
    """Read the player's preferences, goals, and current focus from preferences.json."""
    path = config.preferences_path
    if not path.exists():
        return {
            "note": (
                f"preferences.json not found at {path}. Create it with keys: "
                "goals, dislikes, current_focus, playstyle, character_backstory_notes"
            )
        }
    return json.loads(path.read_text(encoding="utf-8"))
