"""Streamlit Cloud fallback entrypoint.

If a platform defaults to `app.py`, execute `streamlit_app` in a
backward-compatible way:
- Prefer `streamlit_app.main()` when available.
- Fall back to legacy top-level execution if `main` is not defined.
"""

from __future__ import annotations

import importlib
import runpy
from pathlib import Path


def _run_streamlit_app() -> None:
    module = importlib.import_module("streamlit_app")

    entrypoint = getattr(module, "main", None)
    if callable(entrypoint):
        entrypoint()
        return

    legacy_entry = getattr(module, "run", None)
    if callable(legacy_entry):
        legacy_entry()
        return

    # Final fallback: execute file for legacy modules relying on top-level side effects.
    runpy.run_path(str(Path(__file__).with_name("streamlit_app.py")), run_name="__main__")


_run_streamlit_app()
