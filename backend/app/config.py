from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ai_provider: str = "auto"  # "anthropic" | "gemini" | "auto"
    cors_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
