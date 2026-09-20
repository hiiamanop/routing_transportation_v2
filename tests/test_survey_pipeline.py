import csv
import tempfile
import unittest
from pathlib import Path

from scripts.clean_survey_data import ATTRIBUTE_KEYS, clean_rows, read_csv_rows
import numpy as np

from scripts.estimate_mnl import cluster_robust_se, fit_mnl, load_long_format


COLUMNS = [
    "observation_id", "respondent_id", "alternative_index", "label", "optimized_for",
    *ATTRIBUTE_KEYS, "age", "gender", "occupation", "income", "vehicle_ownership",
    "trip_purpose", "transit_frequency", "pref_time", "pref_cost", "pref_comfort",
    "pref_accessibility", "pref_reliability", "chosen",
]


def row(observation_id, respondent_id, index, label, optimized_for, chosen=0,
        time=30, cost=5000, transfers=0, access=0.2, comfort=4, reliability=4):
    values = {
        "observation_id": str(observation_id),
        "respondent_id": respondent_id,
        "alternative_index": str(index),
        "label": label,
        "optimized_for": optimized_for,
        "time_minutes": str(time),
        "cost_rupiah": str(cost),
        "transfers": str(transfers),
        "access_km": str(access),
        "comfort": str(comfort),
        "reliability": str(reliability),
        "chosen": str(chosen),
    }
    return {column: values.get(column, "") for column in COLUMNS}


class CleanSurveyDataTests(unittest.TestCase):
    def test_cleans_choice_sets_without_merging_colliding_ids(self):
        rows = [
            row(198, "respondent-a", 0, "Kendaraan Pribadi", "private_vehicle", 0),
            row(198, "respondent-a", 1, "Preferensi Saya", "preference", 1),
            row(198, "respondent-a", 2, "Termurah", "cost", 0, time=45, cost=0),
            row(198, "respondent-b", 0, "Rekomendasi", "time", 1, time=35),
            row(198, "respondent-b", 1, "Kendaraan Pribadi", "private_vehicle", 0, time=20),
        ]

        cleaned, exclusions, audit = clean_rows(rows)

        by_observation = {}
        for item in cleaned:
            by_observation.setdefault(item["observation_id"], []).append(item)
        self.assertEqual(2, len(by_observation))
        self.assertEqual([], exclusions)
        self.assertEqual(2, audit["valid_observations"])
        self.assertEqual(1, audit["collapsed_duplicate_alternatives"])

        respondent_a = next(items for items in by_observation.values()
                            if items[0]["respondent_id"] == "respondent-a")
        self.assertEqual(2, len(respondent_a))
        chosen = next(item for item in respondent_a if item["chosen"] == "1")
        self.assertEqual("Kendaraan Pribadi", chosen["label"])
        self.assertNotIn("Preferensi Saya", {item["label"] for item in respondent_a})

    def test_excludes_extreme_singleton_and_invalid_choice_sets(self):
        rows = [
            row(1, "extreme", 0, "A", "time", 1, time=1001),
            row(1, "extreme", 1, "B", "cost", 0),
            row(2, "singleton", 0, "A", "time", 1),
            row(3, "no-choice", 0, "A", "time", 0),
            row(3, "no-choice", 1, "B", "cost", 0, time=40),
        ]

        cleaned, exclusions, audit = clean_rows(rows)

        self.assertEqual([], cleaned)
        self.assertEqual(
            {"extreme_value", "fewer_than_two_unique_alternatives", "chosen_count_not_one"},
            {item["reason"] for item in exclusions},
        )
        self.assertEqual(3, audit["excluded_observations"])

    def test_reads_utf8_bom_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "survey.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerow(row(1, "r", 0, "A", "time", 1))

            rows, columns = read_csv_rows(path)

        self.assertEqual("observation_id", columns[0])
        self.assertEqual("1", rows[0]["observation_id"])


class EstimateMnlInputTests(unittest.TestCase):
    def write_csv(self, rows):
        temporary = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        temporary.close()
        path = Path(temporary.name)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(path.unlink)
        return path

    def test_loads_utf8_bom_csv(self):
        path = self.write_csv([
            row(1, "r", 0, "A", "time", 1),
            row(1, "r", 1, "B", "cost", 0, time=40),
        ])
        X_list, chosen, _, _ = load_long_format(path)
        self.assertEqual(1, len(X_list))
        self.assertEqual([0], chosen)

    def test_rejects_choice_set_without_exactly_one_choice(self):
        path = self.write_csv([
            row(1, "r", 0, "A", "time", 1),
            row(1, "r", 1, "B", "cost", 1, time=40),
        ])
        with self.assertRaisesRegex(ValueError, "exactly one chosen alternative"):
            load_long_format(path)

    def test_rejects_single_alternative_choice_set(self):
        path = self.write_csv([row(1, "r", 0, "A", "time", 1)])
        with self.assertRaisesRegex(ValueError, "at least two alternatives"):
            load_long_format(path)

    def test_private_vehicle_asc_uses_transit_as_reference(self):
        path = self.write_csv([
            row(1, "r", 0, "Transit", "time", 1),
            row(1, "r", 1, "Motor", "private_vehicle", 0, time=20),
            row(1, "r", 2, "Ojek", "ride_hailing", 0, time=25),
        ])

        X_list, _, features, _, respondent_ids = load_long_format(
            path, use_private_vehicle_asc=True, return_respondent_ids=True
        )

        self.assertEqual("asc_private_vehicle", features[-1])
        np.testing.assert_array_equal(X_list[0][:, -1], [0.0, 1.0, 0.0])
        self.assertEqual(["r"], respondent_ids)

    def test_clustered_se_combines_scores_from_same_respondent(self):
        X_list = [
            np.array([[0.0], [1.0]]),
            np.array([[0.0], [2.0]]),
            np.array([[0.0], [1.5]]),
            np.array([[0.0], [2.5]]),
        ]
        chosen = [1, 0, 1, 0]
        fit = fit_mnl(X_list, chosen)

        clustered = cluster_robust_se(
            fit["beta"], fit["cov"], X_list, chosen, ["a", "a", "b", "b"]
        )

        self.assertEqual((1,), clustered.shape)
        self.assertTrue(np.isfinite(clustered[0]))
        self.assertGreater(clustered[0], 0)


if __name__ == "__main__":
    unittest.main()
