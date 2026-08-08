#!/usr/bin/env python3
"""
S-3: ubah dataset/survey/choices.jsonl jadi tabel long-format CSV (satu
baris = satu pasangan observasi x alternatif, kolom `chosen` 0/1), digabung
dgn karakteristik responden (S-1) -- lihat src/core/survey_export.py utk
logika intinya (dipakai bareng dgn endpoint unduh GET /api/survey/export).

Usage:
    python scripts/export_long_format.py
    python scripts/export_long_format.py --input dataset/survey/choices.dummy.jsonl \
        --respondents dataset/survey/respondents.dummy.jsonl --output /tmp/out.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from core.survey_export import build_long_format_rows, rows_to_csv, ATTRIBUTE_KEYS  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="dataset/survey/choices.jsonl")
    parser.add_argument("--respondents", default="dataset/survey/respondents.jsonl")
    parser.add_argument("--output", default="dataset/survey/choices_long.csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File tidak ditemukan: {input_path}", file=sys.stderr)
        sys.exit(1)

    rows = build_long_format_rows(input_path, Path(args.respondents))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rows_to_csv(rows), encoding="utf-8")

    n_observations = len({r["observation_id"] for r in rows}) if rows else 0
    n_matched = len({r["observation_id"] for r in rows if r["age"] != ""}) if rows else 0
    n_per_param = n_observations / 30
    print(f"OK - {n_observations} observasi -> {output_path}")
    print(f"   Cukup utk ~{n_per_param:.1f} parameter model (patokan 30 obs/parameter, "
          f"S-4 butuh ~{len(ATTRIBUTE_KEYS)} atribut -> idealnya >=200 observasi)")
    if n_observations > 0:
        pct = 100 * n_matched / n_observations
        print(f"   Karakteristik responden ditemukan: {n_matched}/{n_observations} observasi ({pct:.0f}%)")
        if pct < 100:
            print(f"   -> {n_observations - n_matched} observasi TANPA karakteristik responden "
                  f"(respondent_id belum pernah isi formulir /responden)")


if __name__ == "__main__":
    main()
