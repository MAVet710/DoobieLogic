import unittest
from datetime import date

from doobielogic.engine import CannabisLogicEngine
from doobielogic.models import CannabisInput
from doobielogic.normalizer import normalize_sales_rows_to_input


class TestDoobieLogic(unittest.TestCase):
    def test_engine_analyze_happy_path(self):
        engine = CannabisLogicEngine()
        payload = CannabisInput(
            state="CA",
            period_start="2026-01-01",
            period_end="2026-01-31",
            total_sales_usd=4_200_000,
            transactions=91_000,
            units_sold=238_000,
            avg_basket_usd=46.15,
            inventory_days_on_hand=37,
            discount_rate_pct=12.5,
            price_per_gram_usd=6.8,
            active_retailers=1_240,
            license_violations=1,
            product_mix={
                "flower_pct": 43,
                "vape_pct": 21,
                "edible_pct": 18,
                "concentrate_pct": 11,
                "other_pct": 7,
            },
        )

        output = engine.analyze(payload)
        self.assertEqual(output.state, "CA")
        self.assertTrue(0 <= output.score <= 100)
        self.assertTrue(output.regulation_links["program"].startswith("https://"))
        self.assertGreater(len(output.recommendations), 0)

    def test_normalizer_builds_valid_input(self):
        rows = [
            {
                "sales_usd": 1000,
                "transactions": 20,
                "units_sold": 55,
                "flower_sales_usd": 500,
                "vape_sales_usd": 200,
                "edible_sales_usd": 200,
                "concentrate_sales_usd": 50,
                "inventory_days_on_hand": 28,
                "discount_rate_pct": 11,
                "price_per_gram_usd": 7.2,
                "retailer_id": "r1",
            },
            {
                "sales_usd": 2000,
                "transactions": 30,
                "units_sold": 65,
                "flower_sales_usd": 900,
                "vape_sales_usd": 500,
                "edible_sales_usd": 300,
                "concentrate_sales_usd": 100,
                "inventory_days_on_hand": 32,
                "discount_rate_pct": 9,
                "price_per_gram_usd": 6.8,
                "retailer_id": "r2",
            },
        ]

        normalized = normalize_sales_rows_to_input("CA", date(2026, 1, 1), date(2026, 1, 31), rows)
        self.assertEqual(normalized.state, "CA")
        self.assertEqual(normalized.transactions, 50)
        self.assertAlmostEqual(normalized.total_sales_usd, 3000)
        mix_total = (
            normalized.product_mix.flower_pct
            + normalized.product_mix.vape_pct
            + normalized.product_mix.edible_pct
            + normalized.product_mix.concentrate_pct
            + normalized.product_mix.other_pct
        )
        self.assertTrue(99 <= mix_total <= 101)


if __name__ == "__main__":
    unittest.main()
