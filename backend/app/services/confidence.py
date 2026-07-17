"""
app/services/confidence.py

Pure confidence decay calculation for fuel station availability.
No database calls — only takes timestamps and returns a score dict.
This is the source of truth: confidence is always computed at read-time,
so it degrades correctly regardless of when the endpoint is called.

Decay model:
  - operator source:    linear 100% → 0% over OPERATOR_DECAY_HOURS (default 4h)
  - crowdsource source: linear 80% →  0% over CROWD_DECAY_HOURS (default 1.5h)
    (crowdsource starts lower because individual drivers are less authoritative than the pump operator)
"""

from datetime import datetime, timezone


# Default decay windows (hours). Can be overridden via settings.
OPERATOR_DECAY_HOURS: float = 4.0
CROWDSOURCE_DECAY_HOURS: float = 1.5
CROWDSOURCE_MAX_SCORE: int = 80


def calculate_confidence(
    last_reported_at: datetime,
    source: str,
    current_time: datetime = None,
    operator_decay_hours: float = OPERATOR_DECAY_HOURS,
    crowdsource_decay_hours: float = CROWDSOURCE_DECAY_HOURS,
) -> dict:
    """
    Compute confidence score for a fuel availability update.

    Args:
        last_reported_at: UTC datetime of the last confirmed update.
        source: "operator" or "crowdsource"
        current_time: UTC datetime to compute against (defaults to now; pass explicitly for testing).
        operator_decay_hours: window over which operator confidence decays to 0.
        crowdsource_decay_hours: window over which crowdsource confidence decays to 0.

    Returns:
        {
            "score": int,          # 0–100 inclusive
            "label": str,          # human-readable freshness string
            "is_stale": bool       # True when score == 0 (past full decay window)
        }
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Ensure both datetimes are tz-aware for subtraction
    if last_reported_at.tzinfo is None:
        last_reported_at = last_reported_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = (current_time - last_reported_at).total_seconds()

    if source == "operator":
        decay_seconds = operator_decay_hours * 3600
        max_score = 100
    else:
        # crowdsource
        decay_seconds = crowdsource_decay_hours * 3600
        max_score = CROWDSOURCE_MAX_SCORE

    # Linear decay: score = max_score * (1 - elapsed / decay_window), floored at 0
    if elapsed_seconds <= 0:
        score = max_score
    elif elapsed_seconds >= decay_seconds:
        score = 0
    else:
        ratio = elapsed_seconds / decay_seconds
        score = max(0, round(max_score * (1 - ratio)))

    is_stale = score == 0
    label = _freshness_label(elapsed_seconds, is_stale)

    return {
        "score": score,
        "label": label,
        "is_stale": is_stale,
    }


def _freshness_label(elapsed_seconds: float, is_stale: bool) -> str:
    """Convert elapsed seconds into a human-readable freshness string."""
    if is_stale:
        return "Data expired"

    total_minutes = int(elapsed_seconds // 60)
    if total_minutes < 1:
        return "Just confirmed"
    elif total_minutes < 60:
        return f"Confirmed {total_minutes}m ago"
    else:
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins == 0:
            return f"Confirmed {hours}h ago"
        return f"Confirmed {hours}h {mins}m ago"


def get_best_confidence(updates: list, current_time: datetime = None) -> dict:
    """
    Given a list of AvailabilityUpdate ORM objects (or dicts with the same fields),
    pick the most recent one and return its confidence dict plus the update metadata.

    Returns None if updates list is empty.
    """
    if not updates:
        return {
            "score": 0,
            "label": "No data",
            "is_stale": True,
            "last_reported_at": None,
            "last_update_source": None,
            "reported_status": None,
        }

    # Sort by reported_at descending — take the freshest update
    def _reported_at(u):
        val = u["reported_at"] if isinstance(u, dict) else u.reported_at
        if val is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if isinstance(val, datetime) and val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val

    latest = max(updates, key=_reported_at)

    source = latest["source"] if isinstance(latest, dict) else latest.source
    reported_at = latest["reported_at"] if isinstance(latest, dict) else latest.reported_at
    reported_status = latest["reported_status"] if isinstance(latest, dict) else latest.reported_status

    confidence = calculate_confidence(reported_at, source, current_time)
    return {
        **confidence,
        "last_reported_at": reported_at.isoformat() if reported_at else None,
        "last_update_source": source,
        "reported_status": reported_status,
    }
