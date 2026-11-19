import re
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LEAGUE_PATTERN = re.compile(
    r"https://basketball\.fantasysports\.yahoo\.com/nba/([1-9][0-9]*)(?:/)?$"
)


def league_id_from_url(url: str) -> str:
    match = LEAGUE_PATTERN.fullmatch(url.strip())
    if not match:
        raise ValueError(
            "Use the league root URL: https://basketball.fantasysports.yahoo.com/nba/210163"
        )
    return match.group(1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    yahoo_league_id: str = "210163"
    yahoo_league_url: str = "https://basketball.fantasysports.yahoo.com/nba/210163"
    database_url: str = "sqlite:///./data/fantasy_gm.db"
    local_api_token: str = ""
    ollama_enabled: bool = False
    ollama_model: str = ""
    allowed_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

    @model_validator(mode="after")
    def consistent_target(self):
        if league_id_from_url(self.yahoo_league_url) != self.yahoo_league_id:
            raise ValueError("YAHOO_LEAGUE_ID and YAHOO_LEAGUE_URL must identify the same league")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
