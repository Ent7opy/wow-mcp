from wow_mcp.app import mcp
from wow_mcp.tools import character, gamedata, local  # noqa: F401  -- side-effect imports register tools


if __name__ == "__main__":
    mcp.run()
