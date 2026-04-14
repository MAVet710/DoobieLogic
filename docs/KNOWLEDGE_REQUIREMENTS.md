# DoobieLogic Knowledge Requirements

## Purpose

This document defines the minimum structured data needed for DoobieLogic to act as the intelligence layer behind:
- Buyer Dashboard
- Extraction Command Center
- Compliance Q&A

---

## 1. Buyer Intelligence Data Requirements

### Product Master
- product_name
- brand
- category
- subcategory
- package_size
- strain_type
- form_factor
- sku
- vendor
- producer_license
- state

### Pricing + Margin
- wholesale_cost
- landed_cost
- retail_price
- promo_price
- margin_pct
- discount_depth

### Inventory Health
- on_hand_units
- available_units
- quarantine_units
- reserved_units
- days_on_hand
- avg_daily_units
- avg_weekly_units
- reorder_qty
- reorder_priority
- last_sale_date
- days_since_last_sale

### Assortment + Demand
- category_share
- brand_share
- pack_size_share
- demand_rank
- price_ladder_position
- duplicate_product_cluster
- assortment_gap_flag
- low_coverage_flag
- overconcentration_flag

### Vendor Performance
- fill_rate
- lead_time_days
- case_pack_size
- min_order_qty
- invoice_accuracy
- transfer_delay_rate
- receiving_issue_rate

### Market Context
- state_sales_trend
- category_growth_rate
- active_license_count
- retailer_density
- testing_failure_trend
- regulatory_change_flag

---

## 2. Extraction Intelligence Data Requirements

### Batch Identity
- batch_id_internal
- lot_id
- client_name
- toll_processing_flag
- state
- license_name
- metrc_package_id_input
- metrc_package_id_output
- metrc_manifest_id

### Biomass Inputs
- cultivar
- biomass_type
- biomass_grade
- input_weight_g
- input_moisture_pct
- input_cannabinoid_profile
- input_terpene_profile
- storage_condition
- age_days_from_harvest

### Process Conditions
- extraction_method
- solvent_system
- solvent_grade
- extraction_temperature_c
- extraction_pressure_bar
- soak_time_min
- wash_count
- flow_rate
- recovery_efficiency_pct
- post_process_method
- winterization_flag
- decarb_flag
- filtration_media
- purge_temperature_c
- purge_time_hr
- vacuum_level

### Output Chemistry
- intermediate_output_g
- finished_output_g
- residual_loss_g
- yield_pct
- post_process_efficiency_pct
- neutral_cannabinoid_ratio
- acidic_cannabinoid_ratio
- terpene_retention_estimate
- residual_solvent_risk
- oxidation_risk
- color_grade
- texture_class

### Release + Quality
- coa_status
- qa_hold
- residual_solvent_test_status
- metals_test_status
- pesticide_test_status
- microbial_test_status
- homogeneity_status
- stability_risk_flag
- remediation_flag
- retest_flag

### Operational + Commercial
- operator
- machine_line
- downtime_minutes
- throughput_g_per_hr
- processing_fee_usd
- cogs_usd
- est_revenue_usd
- gross_margin_pct
- promised_completion_date
- sla_status
- invoice_status
- payment_status

### Extraction-Scientist Reasoning Signals
- solvent_selectivity_note
- terpene_preservation_note
- decarb_conversion_note
- purge_sufficiency_note
- phase_behavior_note
- expected_failure_mode
- release_readiness_score

---

## 3. Compliance Intelligence Data Requirements

### Rule Metadata
- state
- program_type
- topic
- subtopic
- rule_summary
- citation
- source_url
- effective_date
- enforcement_date
- last_reviewed_date
- confidence_level

### Regulated Workflow Flags
- packaging_required
- labeling_required
- tracking_required
- testing_required
- transport_manifest_required
- uid_required
- release_status_required
- remediation_allowed
- retesting_allowed

---

## 4. Architecture Principle

### Dashboard responsibilities
- upload files
- map columns
- compute deterministic KPIs
- display tables and controls

### DoobieLogic responsibilities
- enrich with state context
- interpret KPI patterns
- rank operational priorities
- identify scientific/process risk
- output decision-ready recommendations

---

## 5. Minimum API Return Shape

```json
{
  "buyer_signals": [],
  "extraction_signals": [],
  "compliance_flags": [],
  "market_context": [],
  "sources": [],
  "confidence": "high"
}
```
