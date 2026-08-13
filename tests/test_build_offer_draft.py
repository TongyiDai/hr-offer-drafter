import json
import unittest
from pathlib import Path

from scripts.build_offer_draft import build, render_markdown


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "senior-engineer-offer.json"


class OfferDrafterTest(unittest.TestCase):
    def load(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_computes_first_year_cash(self):
        report = build(self.load())
        comp = report["compensation"]
        self.assertEqual(comp["target_bonus_amount"], 93000)
        self.assertEqual(comp["first_year_cash"], 773000)

    def test_equity_stays_out_of_cash_total(self):
        report = build(self.load())
        self.assertEqual(report["compensation"]["equity"]["units"], 4000)
        # first-year cash must equal base + bonus + signing, with no equity value folded in
        self.assertEqual(report["compensation"]["first_year_cash"], 620000 + 93000 + 60000)

    def test_band_position_in_band(self):
        report = build(self.load())
        band = report["band_position"]
        self.assertEqual(band["compa_ratio"], 1.0333)
        self.assertEqual(band["position"], "区间内")

    def test_marks_outside_band(self):
        data = self.load()
        data["compensation"]["base_salary"] = 760000
        report = build(data)
        self.assertEqual(report["band_position"]["position"], "高于带宽")
        reasons = [item["reason"] for item in report["review_queue"]]
        self.assertTrue(any("高于带宽" in reason for reason in reasons))

    def test_pending_approval_enters_review_queue(self):
        report = build(self.load())
        reasons = [item["reason"] for item in report["review_queue"]]
        self.assertTrue(any("薪酬审批" in reason and "pending" in reason for reason in reasons))

    def test_missing_approval_enters_review_queue(self):
        report = build(self.load())
        items = [item["item"] for item in report["review_queue"]]
        # legal approval was not provided in the fixture
        self.assertIn("法务审批", items)

    def test_missing_target_bonus_pct_is_flagged(self):
        data = self.load()
        data["compensation"].pop("target_bonus_pct")
        report = build(data)
        self.assertIsNone(report["compensation"]["target_bonus_amount"])
        self.assertEqual(report["compensation"]["first_year_cash"], 620000 + 60000)
        reasons = [item["reason"] for item in report["review_queue"]]
        self.assertIn("缺目标奖金比例", reasons)

    def test_missing_band_is_flagged(self):
        data = self.load()
        data.pop("band")
        report = build(data)
        self.assertIsNone(report["band_position"])
        reasons = [item["reason"] for item in report["review_queue"]]
        self.assertIn("缺带宽映射", reasons)

    def test_rejects_sensitive_field(self):
        data = self.load()
        data["candidate"]["candidate_name"] = "test"
        with self.assertRaisesRegex(ValueError, "sensitive fields"):
            build(data)

    def test_rejects_extra_field(self):
        data = self.load()
        data["compensation"]["free_text_notes"] = "原始讨论内容"
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            build(data)

    def test_rejects_bonus_pct_over_one(self):
        data = self.load()
        data["compensation"]["target_bonus_pct"] = 15
        with self.assertRaisesRegex(ValueError, "ratio between 0 and 1"):
            build(data)

    def test_rejects_invalid_band(self):
        data = self.load()
        data["band"]["midpoint"] = 480000
        with self.assertRaisesRegex(ValueError, "minimum < midpoint < maximum"):
            build(data)

    def test_markdown_keeps_draft_and_human_boundary(self):
        markdown = render_markdown(build(self.load()))
        self.assertIn("offer 草稿", markdown)
        self.assertIn("人工决策边界", markdown)
        self.assertIn("[候选人姓名]", markdown)


if __name__ == "__main__":
    unittest.main()
