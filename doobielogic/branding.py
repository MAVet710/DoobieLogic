from __future__ import annotations

from pathlib import Path

BRAND_NAME = "DoobieLogic"
BRAND_GREEN = "#0B5D2A"
BRAND_GOLD = "#D4A017"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def packaged_label_image() -> Path:
    return package_root() / "assets" / "doobielogic_label.svg"


def preferred_logo_path() -> Path:
    repo_logo = Path("assets/doobielogic_logo.png")
    if repo_logo.exists():
        return repo_logo
    return packaged_label_image()
