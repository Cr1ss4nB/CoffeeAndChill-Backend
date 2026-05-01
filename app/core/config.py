import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    explicit_url = (os.getenv("DATABASE_URL") or "").strip()
    if explicit_url:
        return explicit_url

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_sslmode = os.getenv("DB_SSLMODE", "require")
    db_dialect = os.getenv("DB_DIALECT", "postgresql+psycopg2")

    if db_user and db_password and db_host:
        safe_password = quote_plus(db_password)
        return (
            f"{db_dialect}://{db_user}:{safe_password}@{db_host}:{db_port}/{db_name}"
            f"?sslmode={db_sslmode}"
        )

    return "postgresql://postgres:postgres@localhost:5432/coffee_chill"


class Settings:
    DATABASE_URL: str = _build_database_url()
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    LOW_STOCK_THRESHOLD: int = int(os.getenv("LOW_STOCK_THRESHOLD", "10"))


settings = Settings()
