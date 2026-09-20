import math
import unittest

from scripts.sensitivity_analysis import (
    likelihood_ratio_test,
    prepare_choice_sets,
    run_sensitivity_analysis,
)
from tests.test_survey_pipeline import row


class SensitivityAnalysisTests(unittest.TestCase):
    def test_prepare_choice_sets_removes_ride_hailing_and_unusable_observations(self):
        rows = [
            row(1, "a", 0, "Transit", "time", 1),
            row(1, "a", 1, "Motor", "private_vehicle", 0, time=20),
            row(1, "a", 2, "Ojek", "ride_hailing", 0, time=25),
            row(2, "b", 0, "Transit", "time", 0),
            row(2, "b", 1, "Ojek", "ride_hailing", 1, time=25),
        ]

        choice_sets, dropped = prepare_choice_sets(rows, exclude_ride_hailing=True)

        self.assertEqual(1, len(choice_sets))
        self.assertEqual({"chosen_ride_hailing": 1}, dropped)
        self.assertEqual(2, len(choice_sets[0]))

    def test_likelihood_ratio_test_uses_correct_degrees_of_freedom(self):
        result = likelihood_ratio_test(full_ll=-100, reduced_ll=-102, degrees_of_freedom=1)
        self.assertAlmostEqual(4.0, result["statistic"])
        self.assertAlmostEqual(math.erfc(math.sqrt(2)), result["p_value"])
        self.assertEqual(1, result["degrees_of_freedom"])

        result_df2 = likelihood_ratio_test(full_ll=-100, reduced_ll=-102, degrees_of_freedom=2)
        self.assertAlmostEqual(math.exp(-2), result_df2["p_value"])

    def test_runs_all_requested_specifications(self):
        import random
        rng = random.Random(7)
        rows = []
        for observation in range(1, 121):
            alternatives = []
            for index, (label, optimized_for) in enumerate((
                ("Transit A", "time"), ("Transit B", "cost"),
                ("Motor", "private_vehicle"),
            )):
                alternatives.append(row(
                    observation, f"r{observation % 25}", index, label, optimized_for,
                    time=rng.uniform(10, 90), cost=rng.uniform(0, 15000),
                    transfers=rng.randint(0, 3), access=rng.uniform(0, 3),
                    comfort=rng.uniform(1, 5), reliability=rng.uniform(1, 5),
                ))
            alternatives[rng.randrange(3)]["chosen"] = "1"
            rows.extend(alternatives)

        report = run_sensitivity_analysis(rows)

        self.assertEqual(
            {"full_asc", "without_access", "without_transfers",
             "without_access_transfers", "without_ride_hailing"},
            set(report["models"]),
        )
        self.assertNotIn("access_km", report["models"]["without_access"]["coefficients"])
        self.assertNotIn("transfers", report["models"]["without_transfers"]["coefficients"])
        self.assertIn("asc_private_vehicle", report["models"]["full_asc"]["coefficients"])
        self.assertIn("without_access", report["likelihood_ratio_tests"])


if __name__ == "__main__":
    unittest.main()
