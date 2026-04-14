# 🔗 DoobieLogic → Buyer Dashboard Bridge

## Goal

Turn DoobieLogic into a **central intelligence API** that feeds buyer decisions instead of duplicating logic inside the dashboard.

---

## Data Flow

Buyer Dashboard → sends:
- mapped inventory data
- state
- category / product filters

DoobieLogic → returns:
- structured risk signals
- reorder recommendations
- compliance flags
- market context

---

## Example Endpoint

```
POST /buyer/intelligence
```

### Request
```
{
  "state": "MA",
  "inventory": {...},
  "focus": "reorder"
}
```

### Response
```
{
  "reorder_now": [...],
  "overstock": [...],
  "compliance_flags": [...],
  "market_context": [...],
  "confidence": "high"
}
```

---

## What DoobieLogic Adds

### 1. Regulatory Context
- packaging + labeling rules
- tracking requirements (Metrc)
- compliance risk signals

### 2. Market Context
- state sales trends
- licensing density
- category saturation

### 3. Buyer Intelligence
- velocity + DOH interpretation
- assortment gaps
- margin pressure signals

---

## Architecture Principle

- Buyer Dashboard = UI + deterministic math
- DoobieLogic = intelligence + interpretation layer

---

## Next Step (Recommended)

Wire `buyer_context_payload()` into API responses so every buyer request is enriched with:
- state rules
- tracking requirements
- testing constraints

This prevents bad decisions like:
- buying non-compliant SKUs
- overloading categories with regulatory friction

---

## End State

DoobieLogic becomes:
- the **brain**
- buyer dashboard becomes the **hands**

