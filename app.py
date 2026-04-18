"""Streamlit Cloud fallback entrypoint.

If a platform defaults to `app.py`, we explicitly call `streamlit_app.main()`
so the UI executes on every Streamlit rerun.
"""

from streamlit_app import main

main()
