from __future__ import annotations

import os


APP_VERSION = "2026.08-grounded-conversations"


def build_info() -> dict[str, str]:
    commit = str(os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT") or "local").strip()
    return {
        "app_version": APP_VERSION,
        "git_commit": commit,
        "git_commit_short": commit[:7] if commit != "local" else "local",
    }
