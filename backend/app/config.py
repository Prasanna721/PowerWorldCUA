from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    cua_api_key: str = ""
    cua_sandbox_name: str = "m-windows-i87anaus"
    target_url: str = "https://www.powerworld.com/download-purchase/demo-software/simulator-demo-download"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
