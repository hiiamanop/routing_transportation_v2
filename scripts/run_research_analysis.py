#!/usr/bin/env python3
"""Jalankan ulang seluruh pipeline analisis penelitian dari satu CSV sumber."""

import argparse
import json
from pathlib import Path

try:
    from scripts.clean_survey_data import clean_rows, read_csv_rows, sha256, write_csv
except ModuleNotFoundError:  # eksekusi langsung
    from clean_survey_data import clean_rows, read_csv_rows, sha256, write_csv


def run_pipeline(source: Path, output_dir: Path, figures: bool = True,
                 models: bool = True, manuscript_dir: Path | None = None) -> dict:
    source, output_dir = Path(source), Path(output_dir)
    rows, columns = read_csv_rows(source)
    if not rows:
        raise ValueError("Dataset sumber kosong.")

    cleaned, exclusions, audit = clean_rows(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = output_dir / "choices_long_clean.csv"
    audit.update({
        "source_file": str(source),
        "source_sha256": sha256(source),
        "output_file": str(clean_path),
    })
    write_csv(clean_path, cleaned, columns)
    write_csv(
        output_dir / "choices_exclusions.csv", exclusions,
        ["source_observation_id", "respondent_id", "reason", "detail", "source_alternatives"],
    )
    (output_dir / "choices_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    result = {"audit": audit}
    if models:
        result["models"] = _run_models(clean_path, output_dir)
    if figures:
        if manuscript_dir is None:
            raise ValueError("manuscript_dir wajib diberikan saat figures=True")
        try:
            from scripts.generate_research_figures import generate_all
        except ModuleNotFoundError:
            from generate_research_figures import generate_all
        result["figures"] = [str(path) for path in generate_all(output_dir, manuscript_dir)]
    return result


def _run_models(clean_path: Path, output_dir: Path) -> dict:
    try:
        from scripts.model_diagnostics import build_diagnostics, estimate_model, write_markdown
        from scripts.sensitivity_analysis import run_sensitivity_analysis, write_markdown as write_sensitivity
    except ModuleNotFoundError:
        from model_diagnostics import build_diagnostics, estimate_model, write_markdown
        from sensitivity_analysis import run_sensitivity_analysis, write_markdown as write_sensitivity

    rows, _ = read_csv_rows(clean_path)
    diagnostics = build_diagnostics(rows)
    diagnostics["models"] = {
        "basic": estimate_model(clean_path),
        "private_vehicle_asc": estimate_model(clean_path, use_asc=True),
    }
    (output_dir / "model_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_markdown(output_dir / "model_diagnostics.md", diagnostics)

    sensitivity = run_sensitivity_analysis(rows)
    (output_dir / "sensitivity_analysis.json").write_text(
        json.dumps(sensitivity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_sensitivity(output_dir / "sensitivity_analysis.md", sensitivity)
    return diagnostics["models"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manuscript-dir", type=Path)
    parser.add_argument("--skip-figures", action="store_true")
    parser.add_argument("--skip-models", action="store_true")
    args = parser.parse_args()
    result = run_pipeline(
        args.input, args.output_dir, figures=not args.skip_figures,
        models=not args.skip_models, manuscript_dir=args.manuscript_dir,
    )
    print(json.dumps(result["audit"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
