from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AdsGenerator API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Target market for live-context gathering (Part 2). Can be overridden per request.
    AREA: str = "Malaysia"

    # ilmu console — OpenAI-compatible GLM-5.1 endpoint
    ILMU_API_KEY: str = ""
    ILMU_BASE_URL: str = "https://api.ilmu.ai/v1"
    ILMU_MODEL: str = "ilmu-glm-5.1"
    # Bumped to 180s because Part 2 (live-context) uses GLM-5.1's web_search tool,
    # which routinely takes 60-90s and previously timed out at the old 60s default.
    ILMU_TIMEOUT_SECONDS: float = 180.0
    # Toggle GLM-5.1 built-in web search. We'll attempt `tools=[{"type": "web_search"}]`;
    # if the API rejects it we silently fall back to a prompt-only directive.
    ILMU_WEB_SEARCH_ENABLED: bool = True

    # Z.AI GLM-Image (text → image, separate from the ilmu-routed GLM-5.1 text API)
    ZAI_API_KEY: str = ""
    ZAI_BASE_URL: str = "https://api.z.ai/api/paas/v4"
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

    # Legacy / Firebase placeholders
    AI_PROVIDER: str = ""
    AI_MODEL: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
