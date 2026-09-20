import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.model_diagnostics import build_diagnostics, estimate_model, write_markdown
from tests.test_survey_pipeline import COLUMNS, row


class ModelDiagnosticsTests(unittest.TestCase):
    def test_reports_choice_distribution_repeated_respondents_and_within_set_variation(self):
        rows = [
            row(1, "same", 0, "Transit", "time", 1, time=30, cost=5000),
            row(1, "same", 1, "Motor", "private_vehicle", 0, time=20, cost=3000),
            row(2, "same", 0, "Transit", "time", 0, time=40, cost=5000),
            row(2, "same", 1, "Motor", "private_vehicle", 1, time=15, cost=3000),
            row(3, "other", 0, "Transit", "time", 1, time=35, cost=5000),
            row(3, "other", 1, "Motor", "private_vehicle", 0, time=25, cost=3000),
        ]

        report = build_diagnostics(rows)

        self.assertEqual(3, report["sample"]["observations"])
        self.assertEqual(2, report["sample"]["respondents"])
        self.assertEqual(1, report["sample"]["respondents_with_multiple_observations"])
        self.assertEqual(2, report["choices"]["by_group"]["transit"])
        self.assertEqual(1, report["choices"]["by_group"]["private_vehicle"])
        self.assertEqual(3, report["within_choice_set_variation"]["time_minutes"]["varying_observations"])
        self.assertEqual(0, report["within_choice_set_variation"]["transfers"]["varying_observations"])

    def test_unique_respondents_use_ordinary_standard_errors_as_primary(self):
        import random
        rng = random.Random(11)
        rows = []
        for observation in range(1, 121):
            alternatives = []
            for index, (label, optimized_for) in enumerate((
                ("Transit A", "time"), ("Transit B", "cost"),
                ("Motor", "private_vehicle"),
            )):
                alternatives.append(row(
                    observation, f"r{observation}", index, label, optimized_for,
                    time=rng.uniform(10, 90), cost=rng.uniform(0, 15000),
                    transfers=rng.randint(0, 3), access=rng.uniform(0, 3),
                    comfort=rng.uniform(1, 5), reliability=rng.uniform(1, 5),
                ))
            alternatives[rng.randrange(3)]["chosen"] = "1"
            rows.extend(alternatives)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            report = estimate_model(path, use_asc=True)
        self.assertEqual(120, report["respondent_clusters"])
        self.assertEqual("ordinary", report["primary_standard_error"])

    def test_markdown_contains_model_comparison(self):
        report = {
            "sample": {"observations": 3, "respondents": 2,
                       "respondents_with_multiple_observations": 1,
                       "observations_with_preferences": 3},
            "choices": {"by_group": {"transit": 2, "private_vehicle": 1, "ride_hailing": 0}},
            "within_choice_set_variation": {},
            "correlations": {},
            "models": {
                "basic": {"rho_squared_mcfadden": 0.1, "log_likelihood": -2.0,
                          "coefficients": {}, "aic": 16.0, "bic": 12.0},
                "private_vehicle_asc": {"rho_squared_mcfadden": 0.2, "log_likelihood": -1.0,
                                        "coefficients": {}, "aic": 16.0, "bic": 13.0},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            write_markdown(path, report)
            text = path.read_text(encoding="utf-8")
        self.assertIn("ASC kendaraan pribadi", text)
        self.assertIn("0.2000", text)


if __name__ == "__main__":
    unittest.main()
