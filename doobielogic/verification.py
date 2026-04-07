from __future__ import annotations

from urllib.parse import urlparse

TRUSTED_EXACT_DOMAINS = {
    "cannabis.ca.gov",
    "cannabis.ny.gov",
    "www.nj.gov",
    "www.oregon.gov",
    "www.pa.gov",
    "www.mass.gov",
}
TRUSTED_SUFFIXES = (".gov", ".edu")


def is_trusted_source(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.netloc or "").lower().split(":")[0]
    return host in TRUSTED_EXACT_DOMAINS or host.endswith(TRUSTED_SUFFIXES)


def verify_sources(sources: list[str]) -> tuple[bool, list[str], list[str]]:
    trusted = [s for s in sources if is_trusted_source(s)]
    untrusted = [s for s in sources if s not in trusted]
    return len(trusted) > 0, trusted, untrusted
