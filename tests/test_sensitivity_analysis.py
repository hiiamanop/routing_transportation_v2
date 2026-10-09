import math
import unittest

from scripts.clean_survey_data import clean_rows
from scripts.sensitivity_analysis import (
    likelihood_ratio_test,
    prepare_choice_sets,
    run_sensitivity_analysis,
    run_unmerged_check,
)
from tests.test_survey_pipeline import row


class SensitivityAnalysisTests(unittest.TestCase):
    def test_prepare_choice_sets_drops_single_alternative_observations(self):
        rows = [
            row(1, "a", 0, "Transit", "time", 1),
            row(1, "a", 1, "Motor", "private_vehicle", 0, time=20),
            row(2, "b", 0, "Motor", "private_vehicle", 1, time=20),
        ]

        choice_sets, dropped = prepare_choice_sets(rows)

        self.assertEqual(1, len(choice_sets))
        self.assertEqual({"fewer_than_two_alternatives": 1}, dropped)
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
             "without_comfort", "without_access_transfers"},
            set(report["models"]),
        )
        self.assertNotIn("access_km", report["models"]["without_access"]["coefficients"])
        self.assertNotIn("transfers", report["models"]["without_transfers"]["coefficients"])
        self.assertIn("asc_private_vehicle", report["models"]["full_asc"]["coefficients"])
        self.assertIn("without_access", report["likelihood_ratio_tests"])


    def test_unmerged_check_keeps_identical_alternatives_as_separate_rows(self):
        import random
        rng = random.Random(11)
        rows = []
        for observation in range(1, 101):
            transit = dict(time=rng.uniform(20, 90), cost=rng.choice((0, 5000, 10000)),
                           transfers=rng.randint(0, 3), access=rng.uniform(0, 3),
                           comfort=rng.uniform(1, 5), reliability=rng.uniform(1, 5))
            motor = dict(time=rng.uniform(5, 40), cost=rng.uniform(500, 4000),
                         transfers=0, access=0, comfort=4, reliability=3)
            alternatives = [
                row(observation, f"r{observation}", 0, "Transit", "time", **transit),
                row(observation, f"r{observation}", 1, "Motor", "private_vehicle", **motor),
                row(observation, f"r{observation}", 2, "Pref", "preference", **motor),
            ]
            alternatives[rng.randrange(3)]["chosen"] = "1"
            rows.extend(alternatives)

        merged_sets, _ = prepare_choice_sets(clean_rows(rows)[0])
        result = run_unmerged_check(rows)

        self.assertEqual(100, result["valid_observations"])
        self.assertEqual({2}, {len(choice_set) for choice_set in merged_sets})
        self.assertIn("asc_private_vehicle", result["model"]["coefficients"])

if __name__ == "__main__":
    unittest.main()
