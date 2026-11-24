"""
General-purpose helper functions.
"""

from datetime import datetime


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    from datetime import timezone
    return datetime.now(timezone.utc)
