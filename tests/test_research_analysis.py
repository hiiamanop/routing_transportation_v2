import json
import tempfile
import unittest
from pathlib import Path

from scripts.clean_survey_data import read_csv_rows, sha256
from scripts.run_research_analysis import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dataset" / "choices_long_20260919_112629_diseragamkan.csv"


class LatestDatasetContractTests(unittest.TestCase):
    def test_latest_source_has_one_observation_per_respondent(self):
        rows, _ = read_csv_rows(SOURCE)
        pairs = {(row["observation_id"], row["respondent_id"]) for row in rows}
        self.assertEqual(400, len(pairs))
        self.assertEqual(400, len({respondent for _, respondent in pairs}))

    def test_pipeline_audit_matches_latest_source_checksum_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(SOURCE, Path(directory), figures=False, models=False)

        self.assertEqual(400, result["audit"]["source_observations"])
        self.assertEqual(400, result["audit"]["source_respondents"])
        self.assertEqual(sha256(SOURCE), result["audit"]["source_sha256"])
        self.assertEqual(
            result["audit"]["valid_observations"],
            result["audit"]["valid_respondents"],
        )


if __name__ == "__main__":
    unittest.main()
