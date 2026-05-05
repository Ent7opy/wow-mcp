import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    client_id: str
    client_secret: str
    default_character: str = ""
    default_realm: str = ""
    default_region: str = "eu"
    preferences_path: Path = field(default_factory=lambda: PROJECT_ROOT / "preferences.json")

    def resolve(
        self,
        character: str | None,
        realm: str | None,
        region: str | None,
    ) -> tuple[str, str, str]:
        c = (character or self.default_character).lower()
        r = (realm or self.default_realm).lower()
        g = (region or self.default_region).lower()
        if not c or not r:
            raise ValueError(
                "character and realm are required — pass them as arguments "
                "or set WOW_CHARACTER_NAME / WOW_REALM in .env"
            )
        return c, r, g


def load_config() -> Config:
    load_dotenv()
    return Config(
        client_id=os.environ["BNET_CLIENT_ID"],
        client_secret=os.environ["BNET_CLIENT_SECRET"],
        default_character=os.getenv("WOW_CHARACTER_NAME", "").lower(),
        default_realm=os.getenv("WOW_REALM", "").lower(),
        default_region=os.getenv("WOW_REGION", "eu").lower(),
    )
