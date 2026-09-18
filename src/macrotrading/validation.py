"""Small strict contracts shared by imports, API routes and domain engines."""
from __future__ import annotations
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

UTC = timezone.utc

def instant(value: str, label='timestamp') -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f'{label} must be an ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{label} must be an ISO timestamp') from exc
    if parsed.tzinfo is None:
        if len(value) != 10:
            raise ValueError(f'{label} must include a timezone')
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

def stamp(value=None):
    value = value or datetime.now(UTC)
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')

def number(value, label, low=-1e15, high=1e15):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be finite and between {low:g} and {high:g}')
    return float(value)

def text(value, label, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{label} must contain 1–{limit} characters')
    return value.strip()

def identifier(value, label='id'):
    value = text(value, label, 128)
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', value):
        raise ValueError(f'{label} contains unsupported characters')
    return value

def boolean(value, label):
    if type(value) is not bool:
        raise ValueError(f'{label} must be true or false, not a string or number')
    return value

def url(value):
    value = text(value, 'source URL', 2000)
    parsed = urlsplit(value)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('source URL must be a public HTTP(S) URL without credentials')
    return value

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def collection(value, label, maximum=5000):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f'{label} must be an array of at most {maximum} items')
    return value
