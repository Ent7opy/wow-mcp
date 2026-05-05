import functools

import httpx
from mcp.server.fastmcp import FastMCP

from wow_mcp.bnet import BnetClient
from wow_mcp.config import load_config


config = load_config()
client = BnetClient(config.client_id, config.client_secret)
mcp = FastMCP("wow-assistant")


def tool_safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            return {
                "error": f"battle.net {e.response.status_code}: {e.response.text[:200]}",
                "status_code": e.response.status_code,
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    return wrapper
