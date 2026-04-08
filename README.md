# DoobieLogic

DoobieLogic is a cannabis operations copilot with **department-specific intelligence** for retail, cultivation, extraction, kitchen, packaging, compliance, and executive workflows.

## What is included now

- Streamlit copilot UI with role/state selection, file upload, department detection, and operations view.
- Built-in curated department knowledge packs (usable before any upload).
- Department-specific parsers and routing.
- Department-specific heuristics and action plans.
- Grounded source context from curated source pack.
- Retail buyer-brain intelligence for retail-shaped files.

## Department-specific modules

- Knowledge packs: `doobielogic/department_knowledge.py`
- Router/parser: `doobielogic/department_router.py`, `doobielogic/department_parsers.py`
- Operations engine: `doobielogic/operations_engine.py`
- Ops logic:
  - `doobielogic/cultivation_ops.py`
  - `doobielogic/extraction_ops.py`
  - `doobielogic/kitchen_ops.py`
  - `doobielogic/packaging_ops.py`
  - `doobielogic/compliance_ops.py`
  - `doobielogic/retail_ops.py`
- Department models:
  - `doobielogic/cultivation_models.py`
  - `doobielogic/extraction_models.py`
  - `doobielogic/kitchen_models.py`
  - `doobielogic/packaging_models.py`
  - `doobielogic/compliance_models.py`

## Built-in learned knowledge (before file upload)

Each department ships with curated static entries (10+ per department) covering:
- recurring risk patterns
- practical operator watchouts
- conservative action framing
- grounded operational/regulatory themes

No live web retrieval is required for this built-in layer.

## Heuristic vs grounded separation

- **Grounded source context**: curated source pack references with labels:
  - `grounding`
  - `confidence`
  - `sources`
- **File-derived operational signals**: heuristic unless explicitly marked as grounded operational/regulatory theme.
- **Compliance outputs** include an explicit notice that operational guidance is **not legal advice**.

## File routing behavior

On upload, the app:
1. Reads CSV rows.
2. Detects likely department from headers.
3. Parses into department-specific structures.
4. Routes to department ops module.
5. Produces learned-knowledge summary + file-derived signals + action plan.

Retail-shaped data falls back to retail parser/buyer-brain flow.

## Sample datasets

- `data/sample_inventory.csv`
- `data/sample_cultivation_ops.csv`
- `data/sample_extraction_ops.csv`
- `data/sample_kitchen_ops.csv`
- `data/sample_packaging_ops.csv`
- `data/sample_compliance_ops.csv`

These are seeded to trigger realistic signals (variance, downtime, delays, reconciliation issues, repeat issues, aging actions).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
streamlit run streamlit_app.py
```

## Run API

```bash
uvicorn doobielogic.api:app --reload
```

## Tests

```bash
python -m pytest -q
```
