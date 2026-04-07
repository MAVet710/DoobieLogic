from __future__ import annotations

from .models import CannabisInput, CannabisOutput
from .regulations import REGULATION_LINKS


class CannabisLogicEngine:
    """Standalone cannabis AI scoring logic."""

    def analyze(self, payload: CannabisInput) -> CannabisOutput:
        market_pressure = self._market_pressure(payload)
        compliance_risk = self._compliance_risk(payload)
        inventory_stress = self._inventory_stress(payload)

        score = max(
            0.0,
            min(
                100.0,
                100 - (market_pressure * 0.4 + compliance_risk * 0.35 + inventory_stress * 0.25),
            ),
        )

        if score >= 80:
            tier = "strong"
        elif score >= 60:
            tier = "watch"
        else:
            tier = "high-risk"

        recs = self._recommendations(payload, market_pressure, compliance_risk, inventory_stress)
        links = REGULATION_LINKS.get(payload.state, {})

        return CannabisOutput(
            state=payload.state,
            score=round(score, 2),
            tier=tier,
            market_pressure=round(market_pressure, 2),
            compliance_risk=round(compliance_risk, 2),
            inventory_stress=round(inventory_stress, 2),
            recommendations=recs,
            regulation_links=links,
        )

    def _market_pressure(self, p: CannabisInput) -> float:
        pressure = 0.0
        if p.discount_rate_pct > 20:
            pressure += 30
        elif p.discount_rate_pct > 10:
            pressure += 15

        if p.price_per_gram_usd < 5:
            pressure += 20

        txn_per_retailer = p.transactions / max(1, p.active_retailers)
        if txn_per_retailer < 40:
            pressure += 25
        elif txn_per_retailer < 70:
            pressure += 10

        if p.product_mix.flower_pct > 60:
            pressure += 10

        return min(100.0, pressure)

    def _compliance_risk(self, p: CannabisInput) -> float:
        risk = 0.0
        if p.license_violations >= 5:
            risk += 60
        elif p.license_violations >= 2:
            risk += 35
        elif p.license_violations == 1:
            risk += 15

        if p.discount_rate_pct > 35:
            risk += 15

        if p.state not in REGULATION_LINKS:
            risk += 20

        return min(100.0, risk)

    def _inventory_stress(self, p: CannabisInput) -> float:
        stress = 0.0
        if p.inventory_days_on_hand > 60:
            stress += 45
        elif p.inventory_days_on_hand > 40:
            stress += 25
        elif p.inventory_days_on_hand > 30:
            stress += 10

        if p.units_sold and p.total_sales_usd / p.units_sold < 12:
            stress += 20

        return min(100.0, stress)

    def _recommendations(self, p: CannabisInput, market_pressure: float, compliance_risk: float, inventory_stress: float) -> list[str]:
        recs: list[str] = []

        if market_pressure >= 30:
            recs.append("Reduce blanket discounting and move to segment-based promotions.")
            recs.append("Shift assortment toward higher-margin derivative categories.")

        if compliance_risk >= 30:
            recs.append("Run weekly compliance audits and pre-file corrective action logs.")
            recs.append("Review current campaign language against state advertising requirements.")

        if inventory_stress >= 25:
            recs.append("Create 30-day inventory burn-down plans for low-turn SKUs.")
            recs.append("Pause inbound POs on categories above target days-on-hand.")

        if not recs:
            recs.append("Maintain current operating plan and monitor KPI drift weekly.")

        program_link = REGULATION_LINKS.get(p.state, {}).get("program")
        if program_link:
            recs.append(f"Compliance reference: {program_link}")

        return recs
