from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "AdsGenerator API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Target market for live-context gathering (Part 2). Can be overridden per request.
    AREA: str = "Malaysia"

    # Z.AI — GLM chat completions (`POST .../paas/v4/chat/completions`) and GLM-Image
    # share the same API base URL and typically the same API key.
    ZAI_API_KEY: str = ""
    ZAI_BASE_URL: str = "https://api.z.ai/api/paas/v4"
    ZAI_CHAT_MODEL: str = "glm-5.1"
    # Live-context web_search routinely takes 60–90s.
    ZAI_CHAT_TIMEOUT_SECONDS: float = 180.0
    ZAI_WEB_SEARCH_ENABLED: bool = True

    # Deprecated: set ZAI_API_KEY instead. Still read if ZAI_API_KEY is empty (migration).
    ILMU_API_KEY: str = ""

    # Z.AI GLM-Image (text → image)
    ZAI_IMAGE_MODEL: str = "glm-image"
    ZAI_IMAGE_QUALITY: str = "hd"  # 'hd' (~20s) or 'standard' (~5-10s)
    ZAI_IMAGE_TIMEOUT_SECONDS: float = 90.0

    # CORS — comma-separated list of allowed origins for the Vite frontend.
    # Defaults cover Vite's two common dev ports (5173 and 4173 preview).
    CORS_ALLOW_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def zai_api_key_resolved(self) -> str:
        """Prefer ZAI_API_KEY; fall back to legacy ILMU_API_KEY during migration."""
        z = (self.ZAI_API_KEY or "").strip()
        if z:
            return z
        return (self.ILMU_API_KEY or "").strip()

    # Legacy / Firebase placeholders
    AI_PROVIDER: str = ""
    AI_MODEL: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""

    model_config = SettingsConfigDict(
        # Resolve to backend/.env regardless of process working directory.
        env_file=str(_BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
