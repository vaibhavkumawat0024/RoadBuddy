"""
app/services/confidence.py

Pure confidence decay calculation for fuel station availability.
No database calls — only takes timestamps and returns a score dict.
This is the source of truth: confidence is always computed at read-time,
so it degrades correctly regardless of when the endpoint is called.

Decay model:
  - operator source with status "available" and ttl_hours set:
    - 100% confidence for the specified ttl_hours duration
    - decays gradually from 100% to 1% over the next 2.0 hours
    - remains at 1% indefinitely (never drops to 0%, never expires)
  - operator source (normal): linear 100% → 0% over OPERATOR_DECAY_HOURS (default 4h)
  - crowdsource source: linear 80% →  0% over CROWD_DECAY_HOURS (default 1.5h)
"""

from datetime import datetime, timezone
from typing import Optional


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
    ttl_hours: Optional[float] = None,
    reported_status: Optional[str] = None,
) -> dict:
    """
    Compute confidence score for a fuel availability update.

    Args:
        last_reported_at: UTC datetime of the last confirmed update.
        source: "operator" or "crowdsource"
        current_time: UTC datetime to compute against (defaults to now).
        operator_decay_hours: default operator decay window.
        crowdsource_decay_hours: default crowdsource decay window.
        ttl_hours: how many hours operator guarantees availability.
        reported_status: petrol | diesel | cng | ev status.

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

    if source == "operator" and reported_status == "available" and ttl_hours is not None:
        # Custom time-decay logic
        if ttl_hours == -1.0:
            score = 100
            is_stale = False
        else:
            ttl_seconds = ttl_hours * 3600.0
            decay_window_seconds = 2.0 * 3600.0  # Decays from 100% to 1% over 2 hours
            
            if elapsed_seconds <= ttl_seconds:
                score = 100
            else:
                decay_elapsed = elapsed_seconds - ttl_seconds
                if decay_elapsed >= decay_window_seconds:
                    score = 1
                else:
                    ratio = decay_elapsed / decay_window_seconds
                    score = max(1, round(100 - (99 * ratio)))
            is_stale = False  # Pinned at 1% so it never expires/disappears completely
    else:
        # Default linear decay
        if source == "operator":
            decay_seconds = operator_decay_hours * 3600
            max_score = 100
        else:
            # crowdsource
            decay_seconds = crowdsource_decay_hours * 3600
            max_score = CROWDSOURCE_MAX_SCORE

        if elapsed_seconds <= 0:
            score = max_score
        elif elapsed_seconds >= decay_seconds:
            score = 0
        else:
            ratio = elapsed_seconds / decay_seconds
            score = max(0, round(max_score * (1 - ratio)))
        is_stale = score == 0

    label = _freshness_label(elapsed_seconds, is_stale, source, reported_status, ttl_hours)

    return {
        "score": score,
        "label": label,
        "is_stale": is_stale,
    }


def _freshness_label(
    elapsed_seconds: float,
    is_stale: bool,
    source: str = None,
    reported_status: str = None,
    ttl_hours: float = None,
) -> str:
    """Convert elapsed seconds into a human-readable freshness string."""
    if source == "operator" and reported_status == "available" and ttl_hours is not None:
        if ttl_hours == -1.0:
            return "Available 24/7 (Guaranteed)"
        ttl_seconds = ttl_hours * 3600.0
        if elapsed_seconds <= ttl_seconds:
            rem_seconds = ttl_seconds - elapsed_seconds
            rem_minutes = int(rem_seconds // 60)
            if rem_minutes < 1:
                return "Guaranteed available (expires in <1m)"
            elif rem_minutes < 60:
                return f"Guaranteed available (expires in {rem_minutes}m)"
            else:
                rem_hours = rem_minutes // 60
                rem_mins = rem_minutes % 60
                if rem_mins == 0:
                    return f"Guaranteed available (expires in {rem_hours}h)"
                return f"Guaranteed available (expires in {rem_hours}h {rem_mins}m)"
        else:
            exp_seconds = elapsed_seconds - ttl_seconds
            exp_minutes = int(exp_seconds // 60)
            
            conf_minutes = int(elapsed_seconds // 60)
            if conf_minutes < 1:
                conf_str = "just now"
            elif conf_minutes < 60:
                conf_str = f"{conf_minutes}m ago"
            else:
                ch = conf_minutes // 60
                cm = conf_minutes % 60
                conf_str = f"{ch}h ago" if cm == 0 else f"{ch}h {cm}m ago"

            if exp_minutes < 1:
                return f"Confirmed {conf_str} (expired <1m ago)"
            elif exp_minutes < 60:
                return f"Confirmed {conf_str} (expired {exp_minutes}m ago)"
            else:
                exp_hours = exp_minutes // 60
                exp_mins = exp_minutes % 60
                exp_str = f"{exp_hours}h ago" if exp_mins == 0 else f"{exp_hours}h {exp_mins}m ago"
                return f"Confirmed {conf_str} (expired {exp_str})"

    # Default logic
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
    ttl_hours = latest["ttl_hours"] if isinstance(latest, dict) else getattr(latest, "ttl_hours", None)

    confidence = calculate_confidence(
        reported_at,
        source,
        current_time,
        ttl_hours=ttl_hours,
        reported_status=reported_status
    )
    return {
        **confidence,
        "last_reported_at": reported_at.isoformat() if reported_at else None,
        "last_update_source": source,
        "reported_status": reported_status,
    }
