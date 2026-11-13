"""Configuración de la aplicación, leída desde variables de entorno o `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de Marmarula. Todas las variables usan el prefijo `MARMARULA_`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MARMARULA_",
        extra="ignore",
    )

    app_name: str = "Marmarula"
    environment: Literal["development", "test", "production"] = "development"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    whatsapp_number: str = Field(default="573000000000", pattern=r"^\d{8,15}$")
    instagram_user: str = Field(default="marmarula", pattern=r"^[A-Za-z0-9._]{1,30}$")
    currency: str = Field(default="COP", pattern=r"^[A-Z]{3}$")
    free_shipping_threshold: int = Field(default=150000, ge=0)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
