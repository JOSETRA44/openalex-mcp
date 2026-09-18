"""Exception -> (error code, exit status, hint) mapping.

Agents branch on the exit status before they parse anything, so the mapping has
to be exhaustive and stable. Every entry also carries a `hint`: the spec's rule
is that a failure must tell the caller what to do next, not just what broke.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ..exceptions import (
    OpenAlexAPIError,
    OpenAlexAuthError,
    OpenAlexConfigError,
    OpenAlexNetworkError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)
from ..tools import InvalidGroupByError
from .render import error_envelope

EXIT_CODES: dict[str, str] = {
    "0": "ok",
    "1": "api",
    "2": "usage",
    "3": "not_found",
    "4": "auth",
    "5": "rate_limit",
    "6": "network",
}

EXIT_BY_CODE: dict[str, int] = {
    "ok": 0,
    "api": 1,
    "internal": 1,
    "usage": 2,
    "not_found": 3,
    "auth": 4,
    "rate_limit": 5,
    "network": 6,
}

# Most specific first — OpenAlexAuthError and friends all subclass
# OpenAlexAPIError, so a naive isinstance chain would collapse them into "api".
_RULES: tuple[tuple[type[BaseException], str, str], ...] = (
    (OpenAlexNotFoundError, "not_found",
     "Check the identifier. DOIs need no 'https://doi.org/' prefix; OpenAlex IDs look like W2741809807."),
    (OpenAlexAuthError, "auth",
     "Set OPENALEX_API_KEY or OPENALEX_EMAIL, or pass --api-key/--email. Free key: https://openalex.org/settings/api"),
    (OpenAlexRateLimitError, "rate_limit",
     "Wait for the rate-limit window to reset, lower --per-page, or set OPENALEX_EMAIL to join the polite pool."),
    (OpenAlexNetworkError, "network",
     "Check connectivity to api.openalex.org and retry; the request never reached the API."),
    (OpenAlexConfigError, "auth",
     "Set OPENALEX_API_KEY or OPENALEX_EMAIL in your environment or .env file. Run 'openalex config' to inspect."),
    (InvalidGroupByError, "usage",
     "Run 'openalex describe aggregate-works --json' to see the accepted group_by values."),
    (OpenAlexAPIError, "api",
     "The API rejected the request. Verify filter syntax with 'openalex filter-guide'."),
    (argparse.ArgumentError, "usage",
     "Run 'openalex describe --json' for the full command manifest."),
)


def classify(exc: BaseException) -> tuple[str, int, str]:
    """Return ``(code, exit_status, hint)`` for ``exc``."""
    for exc_type, code, hint in _RULES:
        if isinstance(exc, exc_type):
            return code, EXIT_BY_CODE[code], hint
    return "internal", EXIT_BY_CODE["internal"], "Unexpected failure — rerun with --format json and report the message."


def report(exc: BaseException, command: str, fmt: str, stream: Any = None) -> int:
    """Emit the failure in the caller's format and return the exit status.

    In machine formats the envelope goes to *stdout* so a pipeline can parse the
    failure; the human one-liner always goes to stderr.
    """
    code, status, hint = classify(exc)
    message = str(exc) or exc.__class__.__name__
    print(f"openalex: {code}: {message}", file=sys.stderr)
    if fmt in ("json", "jsonl"):
        envelope = error_envelope(command, code, message, hint)
        indent = 2 if fmt == "json" else None
        out = stream or sys.stdout
        out.write(json.dumps(envelope, indent=indent, ensure_ascii=False) + "\n")
    return status
