# DoobieLogic

DoobieLogic is a standalone Cannabis AI logic service designed to run now on **Streamlit Community Cloud via GitHub** while keeping API-ready architecture.

## What this includes

1. Cannabis AI scoring engine (market pressure, compliance risk, inventory stress).
2. Sales data normalization pipeline.
3. State regulation links for compliance-aware outputs.
4. Buyer dashboard API endpoints (FastAPI).
5. Community Q&A ingestion so buyers/cannabis professionals can teach the system.
6. Automated source verification so answers must include trusted sources.
7. A **Streamlit app UI** for immediate hosted usage with DoobieLogic brand colors.
8. A seeded cannabis knowledge database for Q&A (cultivation, extraction, packaging, co-pack, kitchen/infusion, retail, sales, compliance, terpenes, cannabinoids, strains, and consumption topics).
9. An Ops Copilot chat layer with role-aware guidance for buyers, sales, cultivation, extraction, and operations teams.

## Streamlit hosting (recommended for now)

Use `streamlit_app.py` as the app entrypoint in Streamlit Cloud.

### Branding setup

- Save your provided logo image as `assets/doobielogic_logo.png`.
- The app auto-uses it in the browser tab icon and header.
- Theme colors are configured in `.streamlit/config.toml` using logo-aligned green/gold palette.

### Troubleshooting deploy startup

- If Streamlit Cloud accidentally points to `doobielogic/api.py`, switch the **Main file path** to `streamlit_app.py`.
- A fallback `app.py` is included to load the Streamlit UI when hosts default to `app.py`.
- `doobielogic/api.py` now uses absolute imports (`from doobielogic...`) to avoid relative-import startup failures.

### Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Streamlit Cloud settings

- **Repository:** this repo (`DoobieLogic`)
- **Branch:** your deployment branch
- **Main file path:** `streamlit_app.py`
- **Python version:** 3.10+

## Package metadata (parent package)

The parent package `doobielogic` exports brand and runtime metadata for downstream apps:

- `__version__`
- `BRAND_NAME`, `BRAND_GREEN`, `BRAND_GOLD`
- `packaged_label_image()` and `preferred_logo_path()`

This ensures relevant info is available directly from the parent package import.

## FastAPI (optional, still available)

```bash
uvicorn doobielogic.api:app --reload
```

## Buyer dashboard endpoints

- `POST /dashboard/{buyer_id}/sync`
- `POST /dashboard/analyze/store`
- `GET /dashboard/{buyer_id}/latest`
- `GET /dashboard/{buyer_id}/kpis`
- `GET /dashboard/{buyer_id}/recommendations`
- `GET /dashboard/buyers`

## Cannabis knowledge assistant

- Seeded data covers grow, post-harvest, extraction, kitchen/infusion, packaging, co-pack, retail buying, sales enablement, compliance and consumer product topics.

- Built-in SQLite knowledge database (`doobielogic_knowledge.db`) auto-seeded with cannabis domain data.
- Streamlit `Knowledge Assistant` tab lets you ask cannabis-specific questions.
- API endpoints:
  - `GET /knowledge/categories`
  - `POST /knowledge/ask`

## Ops Copilot chat

- Streamlit `Ops Copilot` tab provides role-aware responses similar to a domain-specific assistant.
- API endpoints:
  - `POST /chat/message`
  - `POST /chat/feedback`

## Community Q&A endpoints

- `POST /community/questions`
- `GET /community/questions`
- `GET /community/questions/{question_id}`
- `POST /community/questions/{question_id}/answers`

## Verification policy

- Answers require at least one trusted URL source.
- Trusted = `.gov`, `.edu`, or approved regulator domains.
- Accepted answers include a verification report (trusted/untrusted source split and timestamp).
- Human compliance review is still recommended for policy-critical answers.
