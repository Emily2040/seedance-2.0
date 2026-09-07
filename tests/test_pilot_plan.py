from decimal import Decimal
import unittest

from scripts.pilot_plan import ARMS, BRIEFS, CANARY, cost_ceiling, schedule


class PilotPlanTests(unittest.TestCase):
    def test_complete_schedule_and_canary_are_not_double_counted(self):
        rows = schedule()
        self.assertEqual(len(BRIEFS), 12)
        self.assertEqual(len(rows), 48)
        self.assertEqual(len({r["slot"] for r in rows}), 48)
        self.assertEqual(sum(r["phase"] == "canary" for r in rows), 16)
        self.assertTrue(all(r["brief_id"] in CANARY for r in rows[:16]))
        for brief, _ in BRIEFS:
            self.assertEqual({(r["arm"], r["take"]) for r in rows if r["brief_id"] == brief},
                             {(a, t) for a in ARMS for t in (1, 2)})
        self.assertTrue(all(r["status"] == "planned" for r in rows))

    def test_decimal_bound_and_budget_edges(self):
        self.assertEqual(cost_ceiling(Decimal("0.10"), Decimal("4.80")),
                         {"required": Decimal("4.80"), "within_budget": True})
        self.assertFalse(cost_ceiling(Decimal("0.10"), Decimal("4.79"))["within_budget"])
        price = Decimal("1.0000000000000000000000000001")
        self.assertFalse(cost_ceiling(price, Decimal("48"))["within_budget"])

    def test_unknown_nonfinite_negative_and_float_prices_rejected(self):
        for invalid in [None, True, 0.1, Decimal("NaN"), Decimal("Infinity"), Decimal("0"), Decimal("-1")]:
            for first in (True, False):
                with self.subTest(invalid=invalid, first=first), self.assertRaises(ValueError):
                    cost_ceiling(invalid if first else Decimal(1), Decimal(48) if first else invalid)
