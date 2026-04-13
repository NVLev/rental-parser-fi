import os
from typing import Annotated

from pydantic import BaseModel, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseConfig(BaseModel):
    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class BotConfig(BaseModel):
    token: str = Field(..., description="Telegram Bot Token")
    admin_ids: list[int] = Field(default_factory=list, description="Admin user IDs")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("BOT_TOKEN must be valid")
        return v


class ParserConfig(BaseModel):
    check_interval_minutes: int = 30
    request_delay_seconds: float = 1.5
    headless: bool = True               # Playwright


class VuokraoviConfig(BaseModel):
    base_url: str = "https://api.vuokraovi.com/distant/swordsman"
    municipality_code: str = "FI_UUSIMAA_HELSINKI"
    sato_customer_group_id: int = 26    # фильтруем SATO из результатов


class SatoConfig(BaseModel):
    base_url: str = "https://www.sato.fi/en/rental-apartments/helsinki"


class PaginationConfig(BaseModel):
    leads_page_size: int = 5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    run: RunConfig = Field(default_factory=RunConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # bot: Annotated[BotConfig, Field()]
    parser: ParserConfig = Field(default_factory=ParserConfig)
    vuokraovi: VuokraoviConfig = Field(default_factory=VuokraoviConfig)
    sato: SatoConfig = Field(default_factory=SatoConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)


settings = Settings()

# print(settings.model_dump())
