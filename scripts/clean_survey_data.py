#!/usr/bin/env python3
"""Bentuk dataset MNL bersih tanpa mengubah CSV survei asli."""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ATTRIBUTE_KEYS = (
    "time_minutes", "cost_rupiah", "transfers", "access_km", "comfort", "reliability",
)
MAX_TIME_MINUTES = 1000.0
MAX_COST_RUPIAH = 100_000.0
WIB_TZ = timezone(timedelta(hours=7))


def read_csv_rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def _signature(row):
    return tuple(float(row[key]) for key in ATTRIBUTE_KEYS)


def _observation_key(row):
    return row["observation_id"], row.get("respondent_id", "")


def clean_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[_observation_key(row)].append(row)

    cleaned = []
    exclusions = []
    reason_counts = Counter()
    duplicate_count = 0

    for source_key, choice_set in grouped.items():
        source_observation_id, respondent_id = source_key

        try:
            extreme = any(
                float(row["time_minutes"]) > MAX_TIME_MINUTES
                or float(row["cost_rupiah"]) > MAX_COST_RUPIAH
                for row in choice_set
            )
            for row in choice_set:
                values = [float(row[key]) for key in ATTRIBUTE_KEYS]
                if any(value < 0 or value != value or abs(value) == float("inf") for value in values):
                    raise ValueError("attribute values must be finite and non-negative")
        except (KeyError, TypeError, ValueError) as error:
            reason = "invalid_attribute"
            detail = str(error)
        else:
            reason = "extreme_value" if extreme else ""
            detail = (
                f"time_minutes>{MAX_TIME_MINUTES:g} or cost_rupiah>{MAX_COST_RUPIAH:g}"
                if extreme else ""
            )

        if reason:
            exclusions.append({
                "source_observation_id": source_observation_id,
                "respondent_id": respondent_id,
                "reason": reason,
                "detail": detail,
                "source_alternatives": len(choice_set),
            })
            reason_counts[reason] += 1
            continue

        identical = defaultdict(list)
        for row in choice_set:
            identical[_signature(row)].append(row)

        collapsed = []
        for alternatives in identical.values():
            duplicate_count += len(alternatives) - 1
            kept = next(
                (row for row in alternatives if row.get("optimized_for") != "preference"),
                alternatives[0],
            ).copy()
            kept["chosen"] = "1" if any(float(row["chosen"]) == 1 for row in alternatives) else "0"
            collapsed.append(kept)

        if len(collapsed) < 2:
            reason = "fewer_than_two_unique_alternatives"
            detail = f"only {len(collapsed)} unique alternative(s)"
        elif sum(float(row["chosen"]) == 1 for row in collapsed) != 1:
            reason = "chosen_count_not_one"
            detail = "choice set must contain exactly one chosen alternative"
        else:
            reason = ""
            detail = ""

        if reason:
            exclusions.append({
                "source_observation_id": source_observation_id,
                "respondent_id": respondent_id,
                "reason": reason,
                "detail": detail,
                "source_alternatives": len(choice_set),
            })
            reason_counts[reason] += 1
            continue

        new_observation_id = str(len({row["observation_id"] for row in cleaned}))
        collapsed.sort(key=lambda row: int(row["alternative_index"]))
        for new_index, row in enumerate(collapsed):
            row["observation_id"] = new_observation_id
            row["alternative_index"] = str(new_index)
            row["chosen"] = str(int(float(row["chosen"]) == 1))
            cleaned.append(row)

    audit = {
        "source_rows": len(rows),
        "source_observations": len(grouped),
        "source_respondents": len({key[1] for key in grouped if key[1]}),
        "valid_observations": len({_observation_key(row) for row in cleaned}),
        "valid_respondents": len({row.get("respondent_id", "") for row in cleaned if row.get("respondent_id")}),
        "clean_rows": len(cleaned),
        "excluded_observations": len(exclusions),
        "exclusions_by_reason": dict(sorted(reason_counts.items())),
        "collapsed_duplicate_alternatives": duplicate_count,
        "thresholds": {
            "max_time_minutes": MAX_TIME_MINUTES,
            "max_cost_rupiah": MAX_COST_RUPIAH,
        },
    }
    return cleaned, exclusions, audit


def write_csv(path, rows, fieldnames):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--exclusions", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    rows, columns = read_csv_rows(args.input)
    cleaned, exclusions, audit = clean_rows(rows)
    audit.update({
        "generated_at": datetime.now(WIB_TZ).isoformat(),
        "source_file": str(Path(args.input)),
        "source_sha256": sha256(args.input),
        "output_file": str(Path(args.output)),
    })

    write_csv(args.output, cleaned, columns)
    write_csv(
        args.exclusions,
        exclusions,
        ["source_observation_id", "respondent_id", "reason", "detail", "source_alternatives"],
    )
    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
