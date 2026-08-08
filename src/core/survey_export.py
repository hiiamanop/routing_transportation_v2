"""
Logika inti S-3 (ubah choices.jsonl -> tabel long-format), dipakai bareng
oleh scripts/export_long_format.py (CLI) dan api/app.py (endpoint unduh) --
satu sumber kebenaran, supaya format keduanya tidak diam-diam mencar.
"""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Union

ATTRIBUTE_KEYS = ("time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability")
RESPONDENT_KEYS = ("age", "gender", "occupation", "income", "vehicle_ownership",
                   "trip_purpose", "transit_frequency")

COLUMNS = (
    "observation_id", "respondent_id", "alternative_index", "label", "optimized_for",
    *ATTRIBUTE_KEYS, *RESPONDENT_KEYS, "chosen",
)


def load_respondents(path: Union[str, Path]) -> Dict[str, dict]:
    """respondent_id -> karakteristik (dict RESPONDENT_KEYS), atau {} kalau
    file tidak ada. Kalau satu respondent_id muncul >1x, dipakai baris
    TERAKHIR (isian formulir terbaru dianggap paling representatif)."""
    path = Path(path)
    if not path.exists():
        return {}

    respondents = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            rid = record.get("respondent_id")
            if rid:
                respondents[rid] = {k: record.get(k, "") for k in RESPONDENT_KEYS}
    return respondents


def _to_long_rows(observation: dict, observation_id: int, respondents: Dict[str, dict]):
    """Satu observasi (choice_set + chosen_index) -> baris long-format, satu per alternatif."""
    chosen_index = observation["chosen_index"]
    respondent_id = observation.get("respondent_id", "")
    respondent_traits = respondents.get(respondent_id, {k: "" for k in RESPONDENT_KEYS})

    for i, alt in enumerate(observation["choice_set"]):
        row = {
            "observation_id": observation_id,
            "respondent_id": respondent_id,
            "alternative_index": i,
            "label": alt.get("label", ""),
            "optimized_for": alt.get("optimized_for", ""),
            "chosen": 1 if i == chosen_index else 0,
            **respondent_traits,
        }
        attrs = alt.get("attributes", {})
        for key in ATTRIBUTE_KEYS:
            row[key] = attrs.get(key, "")
        yield row


def build_long_format_rows(choices_path: Union[str, Path],
                           respondents_path: Union[str, Path]) -> List[dict]:
    """Baca choices.jsonl (+ respondents.jsonl utk join), return list baris
    long-format (dict per baris, kolom = COLUMNS). Baris JSON rusak dilewati."""
    respondents = load_respondents(respondents_path)

    rows = []
    n_observations = 0
    with open(choices_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                observation = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.extend(_to_long_rows(observation, n_observations, respondents))
            n_observations += 1

    return rows


def rows_to_csv(rows: Iterable[dict]) -> str:
    """Rows -> teks CSV (string), supaya pemanggil bebas menyimpan ke file
    ATAU mengirim langsung sbg HTTP response tanpa lewat disk."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
