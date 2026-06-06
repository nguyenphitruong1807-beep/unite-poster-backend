from functools import lru_cache
import os


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Unite Poster Backend")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8080"))

    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://kclwqffwkxraryunmssd.supabase.co")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "poster-assets")

    REQUIRE_AUTH_FOR_MUTATIONS = os.getenv("REQUIRE_AUTH_FOR_MUTATIONS", "false").lower() == "true"
    AUTO_UPLOAD_OUTPUTS = os.getenv("AUTO_UPLOAD_OUTPUTS", "true").lower() == "true"
    JOB_LOGGING_ENABLED = os.getenv("JOB_LOGGING_ENABLED", "true").lower() == "true"

    TMP_DIR = os.getenv("TMP_DIR", "/tmp/unite_poster_backend")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.TMP_DIR, exist_ok=True)
    return settings
