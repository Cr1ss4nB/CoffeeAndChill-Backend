from datetime import datetime, timezone


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp for model defaults and business logic."""
    return datetime.now(timezone.utc)
