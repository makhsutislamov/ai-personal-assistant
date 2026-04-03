from __future__ import annotations

import re
from dataclasses import dataclass

# ---- Pattern definitions (one per sensitivity category) ----
# Each entry: (label, compiled_pattern)

_RAW_PATTERNS: list[tuple[str, str]] = [
    # Generic API keys and tokens
    ("api_key", r"(?i)(api[_\-]?key|api[_\-]?secret)\s*[:=]\s*\S+"),
    ("bearer_token", r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    # AWS keys
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("aws_secret_key", r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[:=]\s*\S+"),
    # OpenAI / general sk- keys
    ("sk_key", r"sk-[A-Za-z0-9]{20,}"),
    # Passwords
    ("password_kv", r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    # Private keys
    ("private_key_pem", r"-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----"),
    # Connection strings (common patterns for SQL, Redis, MongoDB)
    ("connection_string_password", r"(?i)(Server|Host|Data Source)=[^;]+;[^;]*Password=[^;]+"),
    ("mongodb_uri", r"mongodb(?:\+srv)?://[^:]+:[^@]+@"),
    # GitHub tokens
    ("github_token", r"ghp_[A-Za-z0-9]{20,}"),
    # Slack tokens
    ("slack_token", r"xox[baprs]-[A-Za-z0-9\-]+"),
    # Generic secret patterns
    ("secret_kv", r"(?i)(secret|token)[_\-]?\w*\s*[:=]\s*[A-Za-z0-9_\-]{8,}"),
]

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pattern)) for label, pattern in _RAW_PATTERNS
]


@dataclass
class SensitiveMatch:
    label: str
    matched_text: str


def detect_sensitive(text: str) -> list[SensitiveMatch]:
    """Return all sensitive matches found in the given text."""
    matches: list[SensitiveMatch] = []
    for label, pattern in PATTERNS:
        for m in pattern.finditer(text):
            # Redact the full match to avoid leaking through logs
            matches.append(SensitiveMatch(label=label, matched_text="[REDACTED]"))
    return matches
