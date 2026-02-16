"""애플리케이션 설정"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """환경 변수 기반 설정"""

    database_url: str = "postgresql://yummy:yummy_secret@localhost:5432/yummy"
    secret_key: str = "change-me-in-production-use-32-chars"
    cookie_domain: str = "localhost"
    upload_dir: str = "./uploads"
    session_cookie_name: str = "yummy_session"
    session_max_age_seconds: int = 86400 * 7  # 7일
    cookie_secure: bool = False  # Cloudflare Tunnel HTTPS 시 True로 설정
    kakao_rest_api_key: str = Field(default="", description="Kakao 지도 Geocoding API 키")
    kakao_javascript_key: str = Field(default="", description="Kakao 지도 Web API JavaScript 키")

    model_config = {"env_prefix": ""}


@lru_cache
def get_settings() -> Settings:
    return Settings()
