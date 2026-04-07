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

## Streamlit hosting (recommended for now)

Use `streamlit_app.py` as the app entrypoint in Streamlit Cloud.

### Branding setup

- Save your provided logo image as `assets/doobielogic_logo.png`.
- The app auto-uses it in the browser tab icon and header.
- Theme colors are configured in `.streamlit/config.toml` using logo-aligned green/gold palette.

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
