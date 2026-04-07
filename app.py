"""Streamlit Cloud fallback entrypoint.

If a platform defaults to `app.py`, importing this module will execute the
Streamlit UI defined in `streamlit_app.py`.
"""

from streamlit_app import *  # noqa: F401,F403
