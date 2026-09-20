# Bilingual Mode Choice Manuscript Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menghitung ulang analisis dari dataset terbaru 400 responden, menghasilkan enam figure Indonesia dan Inggris, lalu menyusun dua manuskrip lengkap sesuai template Jurnal Kejuruteraan.

**Architecture:** CSV sumber tetap tidak diubah. Pipeline pembersihan menghasilkan dataset final dan audit; skrip estimasi/diagnostik/sensitivitas membaca dataset final dan menulis JSON sebagai sumber angka tunggal; generator figure membaca JSON tersebut untuk menghasilkan SVG dan PNG bilingual; manuskrip Indonesia dan Inggris memakai angka serta figure dari artefak yang sama.

**Tech Stack:** Python 3.12 standard library, NumPy, Matplotlib, unittest, Markdown, SVG, PNG 300 dpi.

**Spec:** `docs/superpowers/specs/2026-09-20-bilingual-mode-choice-manuscript-design.md`

## Global Constraints

- Dataset sumber: `dataset/choices_long_20260919_112629_diseragamkan.csv` dan tidak boleh diubah.
- Dataset terbaru mewakili 400 responden berbeda, satu observasi per responden.
- Eksklusi: `time_minutes > 1000`, `cost_rupiah > 100000`, kurang dari dua alternatif unik, atau jumlah pilihan bukan satu.
- Artikel utama berfokus pada MNL; routing hanya instrumen pembentuk alternatif.
- Dua paket lengkap terpisah: Bahasa Indonesia dan Bahasa Inggris.
- Enam figure per bahasa; setiap figure tersedia dalam SVG dan PNG 300 dpi, lebar 17 cm.
- Naskah anonim, usia tidak ditampilkan, pendanaan tetap placeholder, nama/nomor komite etik tidak dicantumkan.
- Pilihan disebut intended route choice untuk perjalanan rutin nyata, bukan revealed preference.
- Referensi eksternal hanya dipakai bila metadata penerbit/DOI/dokumen resmi dapat diverifikasi.
- Semua perubahan perilaku mengikuti TDD; setiap test harus diamati gagal sebelum implementasi.

---

## File Structure

**Create**

- `scripts/run_research_analysis.py` — orkestrator satu perintah untuk audit, estimasi, diagnostik, sensitivitas, dan figure.
- `scripts/generate_research_figures.py` — generator enam figure bilingual dari artefak analisis.
- `tests/test_research_analysis.py` — kontrak pipeline terbaru dan konsistensi sampel.
- `tests/test_research_figures.py` — kontrak 24 file figure, dimensi, DPI, bahasa, dan kesamaan data.
- `tests/test_manuscripts.py` — pemeriksaan struktur, abstrak, figure, tabel, placeholder, dan angka kedua manuskrip.
- `docs/manuscript/id/manuscript.md` — manuskrip Bahasa Indonesia.
- `docs/manuscript/en/manuscript.md` — manuskrip English.
- `docs/manuscript/id/figures/*.{svg,png}` — enam figure Indonesia.
- `docs/manuscript/en/figures/*.{svg,png}` — enam figure English.
- `docs/manuscript/references_verified.json` — metadata referensi terverifikasi dan URL sumber.

**Modify**

- `scripts/requirements.txt` — tambahkan Matplotlib sebagai dependency skrip riset.
- `scripts/clean_survey_data.py` — jika verifikasi dataset terbaru menemukan asumsi lama yang tak sesuai, ubah hanya minimal.
- `scripts/estimate_mnl.py` — pastikan inferensi utama memakai SE biasa untuk satu observasi per responden.
- `scripts/model_diagnostics.py` — keluaran dataset terbaru dan istilah kelompok moda yang netral.
- `scripts/sensitivity_analysis.py` — keluaran dataset terbaru dan label transportasi nonpublik berbayar.
- `docs/RENCANA_SISTEM.md` — perbarui checkpoint penelitian setelah hasil final tersedia.

**Generated analysis artifacts**

- `dataset/survey/processed/choices_long_clean.csv`
- `dataset/survey/processed/choices_exclusions.csv`
- `dataset/survey/processed/choices_audit.json`
- `dataset/survey/processed/mnl_basic.jsonl`
- `dataset/survey/processed/mnl_private_vehicle_asc.jsonl`
- `dataset/survey/processed/mnl_interactions_exploratory.jsonl`
- `dataset/survey/processed/model_diagnostics.json`
- `dataset/survey/processed/model_diagnostics.md`
- `dataset/survey/processed/sensitivity_analysis.json`
- `dataset/survey/processed/sensitivity_analysis.md`

---

### Task 1: Rebuild and lock the final analytical dataset

**Files:**
- Create: `tests/test_research_analysis.py`
- Create: `scripts/run_research_analysis.py`
- Modify: `scripts/clean_survey_data.py`
- Generate: `dataset/survey/processed/choices_long_clean.csv`
- Generate: `dataset/survey/processed/choices_exclusions.csv`
- Generate: `dataset/survey/processed/choices_audit.json`

**Interfaces:**
- Consumes: source CSV path.
- Produces: `run_pipeline(source: Path, output_dir: Path, figures: bool = True) -> dict` and audit JSON with `source_observations`, `source_respondents`, `valid_observations`, `valid_respondents`, `source_sha256`, and exclusions.

- [ ] **Step 1: Write failing dataset-contract tests**

```python
class LatestDatasetContractTests(unittest.TestCase):
    def test_latest_source_has_one_observation_per_respondent(self):
        rows, _ = read_csv_rows(SOURCE)
        pairs = {(r["observation_id"], r["respondent_id"]) for r in rows}
        self.assertEqual(400, len(pairs))
        self.assertEqual(400, len({respondent for _, respondent in pairs}))

    def test_pipeline_audit_matches_latest_source_checksum_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_pipeline(SOURCE, Path(directory), figures=False)
        self.assertEqual(400, result["audit"]["source_observations"])
        self.assertEqual(400, result["audit"]["source_respondents"])
        self.assertEqual(sha256(SOURCE), result["audit"]["source_sha256"])
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m unittest tests/test_research_analysis.py -v
```

Expected: import failure for `scripts.run_research_analysis` or missing audit respondent fields.

- [ ] **Step 3: Implement minimal orchestrator and audit respondent counts**

`run_pipeline` must call the existing cleaning functions, overwrite generated files in the requested output directory, and return parsed audit data. It must refuse an empty source and never modify the source file.

- [ ] **Step 4: Run tests and rebuild final clean data**

```bash
python -m unittest tests/test_research_analysis.py tests/test_survey_pipeline.py -v
python scripts/run_research_analysis.py \
  --input dataset/choices_long_20260919_112629_diseragamkan.csv \
  --output-dir dataset/survey/processed \
  --skip-figures
```

Expected: PASS; audit checksum equals current source; source count is 400 respondents/observations.

- [ ] **Step 5: Validate every final choice set**

```bash
python - <<'PY'
import csv, json
from collections import defaultdict
rows=list(csv.DictReader(open('dataset/survey/processed/choices_long_clean.csv', encoding='utf-8')))
sets=defaultdict(list)
for row in rows: sets[row['observation_id']].append(row)
assert all(len(v) >= 2 for v in sets.values())
assert all(sum(int(r['chosen']) for r in v) == 1 for v in sets.values())
assert all(float(r['time_minutes']) <= 1000 for r in rows)
assert all(float(r['cost_rupiah']) <= 100000 for r in rows)
audit=json.load(open('dataset/survey/processed/choices_audit.json'))
assert audit['valid_observations'] == len(sets)
print(audit)
PY
```

- [ ] **Step 6: Commit**

```bash
git add scripts/clean_survey_data.py scripts/run_research_analysis.py tests/test_research_analysis.py tests/test_survey_pipeline.py dataset/choices_long_20260919_112629_diseragamkan.csv dataset/survey/processed/choices_long_clean.csv dataset/survey/processed/choices_exclusions.csv dataset/survey/processed/choices_audit.json
git commit -m "feat: rebuild final survey analysis dataset"
```

---

### Task 2: Re-estimate all models from the latest dataset

**Files:**
- Modify: `scripts/estimate_mnl.py`
- Modify: `scripts/model_diagnostics.py`
- Modify: `scripts/sensitivity_analysis.py`
- Modify: `tests/test_survey_pipeline.py`
- Modify: `tests/test_model_diagnostics.py`
- Modify: `tests/test_sensitivity_analysis.py`
- Generate: model JSON/Markdown artifacts under `dataset/survey/processed/`

**Interfaces:**
- Consumes: final clean CSV from Task 1.
- Produces: basic model, ASC model, exploratory interaction model, diagnostics, and sensitivity reports. All reports include exact sample size and ordinary SE; clustered SE may be retained only as a non-primary compatibility field.

- [ ] **Step 1: Write failing inference and freshness tests**

Add tests asserting:

```python
def test_primary_report_uses_ordinary_standard_errors_for_unique_respondents():
    report = estimate_model(clean_path, use_asc=True)
    self.assertEqual(report["n_observations"], report["respondent_clusters"])
    self.assertEqual("ordinary", report["primary_standard_error"])


def test_generated_reports_use_final_clean_sample():
    diagnostics = json.loads(DIAGNOSTICS.read_text())
    sensitivity = json.loads(SENSITIVITY.read_text())
    audit = json.loads(AUDIT.read_text())
    self.assertEqual(audit["valid_observations"], diagnostics["sample"]["observations"])
    self.assertEqual(audit["valid_observations"], sensitivity["models"]["full_asc"]["n_observations"])
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m unittest tests/test_survey_pipeline.py tests/test_model_diagnostics.py tests/test_sensitivity_analysis.py tests/test_research_analysis.py -v
```

Expected: missing `primary_standard_error` or stale sample mismatch.

- [ ] **Step 3: Implement minimal report metadata and terminology updates**

Add `primary_standard_error: "ordinary"` when all respondent IDs are unique. Preserve numerical fitting logic. Replace report-facing `ride_hailing` labels with `paid_non_public_transport` while retaining raw `optimized_for` parsing for backward compatibility.

- [ ] **Step 4: Re-run all estimations through the orchestrator**

```bash
python scripts/run_research_analysis.py \
  --input dataset/choices_long_20260919_112629_diseragamkan.csv \
  --output-dir dataset/survey/processed \
  --skip-figures
```

Expected generated files include basic, ASC, diagnostics, and sensitivity results based on the new checksum.

- [ ] **Step 5: Run model tests and synthetic mathematical checks**

```bash
python -m unittest discover -s tests -v
python scripts/estimate_mnl.py --demo
python -m compileall -q scripts src api
```

Expected: all tests PASS; both synthetic estimator checks PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/estimate_mnl.py scripts/model_diagnostics.py scripts/sensitivity_analysis.py tests dataset/survey/processed
git commit -m "feat: estimate final mode choice models"
```

---

### Task 3: Research and lock verifiable references

**Files:**
- Create: `docs/manuscript/references_verified.json`

**Interfaces:**
- Consumes: publisher pages, DOI metadata, and official documents.
- Produces: JSON array with `id`, `authors`, `year`, `title`, `source`, `volume`, `issue`, `pages`, `doi`, `url`, `claim_scope`, and `verified_at`.

- [ ] **Step 1: Search primary literature and official context sources**

Minimum coverage:

- foundational MNL/discrete choice source;
- recent mode-choice application literature;
- integrated public transport/intermodality literature;
- official Palembang/LRT/public transport context;
- stated/intended choice methodological distinction;
- McFadden fit interpretation and model-selection metrics.

Use `search_web` to discover and `web_fetch` or publisher pages to verify metadata. Do not cite search snippets.

- [ ] **Step 2: Create verified metadata ledger**

Example record:

```json
{
  "id": "train2009",
  "authors": ["Kenneth E. Train"],
  "year": 2009,
  "title": "Discrete Choice Methods with Simulation",
  "source": "Cambridge University Press",
  "volume": "",
  "issue": "",
  "pages": "",
  "doi": "",
  "url": "https://eml.berkeley.edu/books/choice2.html",
  "claim_scope": ["MNL probability", "maximum likelihood", "IIA"],
  "verified_at": "2026-09-20"
}
```

- [ ] **Step 3: Validate the ledger mechanically**

```bash
python - <<'PY'
import json
p='docs/manuscript/references_verified.json'
refs=json.load(open(p))
required={'id','authors','year','title','source','url','claim_scope','verified_at'}
assert len(refs) >= 12
assert len({r['id'] for r in refs}) == len(refs)
assert all(required <= set(r) for r in refs)
assert all(r['url'].startswith('http') for r in refs)
print(len(refs), 'verified references')
PY
```

- [ ] **Step 4: Commit**

```bash
git add -f docs/manuscript/references_verified.json
git commit -m "docs: add verified mode choice references"
```

---

### Task 4: Generate six bilingual research figures

**Files:**
- Create: `scripts/generate_research_figures.py`
- Create: `tests/test_research_figures.py`
- Modify: `scripts/requirements.txt`
- Generate: `docs/manuscript/id/figures/*.{svg,png}`
- Generate: `docs/manuscript/en/figures/*.{svg,png}`

**Interfaces:**
- Consumes: audit, diagnostics, sensitivity JSON, and final clean CSV.
- Produces: `generate_all(processed_dir: Path, manuscript_dir: Path) -> list[Path]`, exactly 24 paths (6 figures × 2 languages × 2 formats).

- [ ] **Step 1: Add Matplotlib dependency**

Append:

```text
matplotlib>=3.8
```

No additional plotting dependency is allowed.

- [ ] **Step 2: Write failing figure-contract tests**

```python
class ResearchFigureTests(unittest.TestCase):
    def test_generates_six_figures_in_two_languages_and_two_formats(self):
        paths = generate_all(PROCESSED, self.output)
        self.assertEqual(24, len(paths))
        for language in ("id", "en"):
            self.assertEqual(6, len(list((self.output/language/"figures").glob("*.svg"))))
            self.assertEqual(6, len(list((self.output/language/"figures").glob("*.png"))))

    def test_png_is_300_dpi_and_approximately_17_cm_wide(self):
        generate_all(PROCESSED, self.output)
        png = next((self.output/"id"/"figures").glob("*.png"))
        with Image.open(png) as image:
            self.assertAlmostEqual(300, image.info["dpi"][0], delta=1)
            self.assertAlmostEqual(2008, image.width, delta=4)

    def test_language_specific_svg_text(self):
        generate_all(PROCESSED, self.output)
        id_svg=(self.output/"id"/"figures"/"figure_02_distribusi_pilihan.svg").read_text()
        en_svg=(self.output/"en"/"figures"/"figure_02_choice_distribution.svg").read_text()
        self.assertIn("Transportasi publik", id_svg)
        self.assertIn("Public transport", en_svg)
```

Use standard library XML parsing for SVG validity. Pillow is already available through Matplotlib; if direct import is unavailable, inspect PNG metadata with Matplotlib’s image reader and add no separate dependency unless necessary.

- [ ] **Step 3: Run tests and verify RED**

```bash
python -m unittest tests/test_research_figures.py -v
```

Expected: module import failure.

- [ ] **Step 4: Implement shared bilingual generator**

Required functions:

```python
def save_figure(fig, svg_path: Path, png_path: Path) -> None: ...
def figure_01_research_flow(language: str, data: dict): ...
def figure_02_choice_distribution(language: str, data: dict): ...
def figure_03_attribute_diagnostics(language: str, data: dict): ...
def figure_04_mnl_coefficients(language: str, data: dict): ...
def figure_05_model_fit(language: str, data: dict): ...
def figure_06_coefficient_stability(language: str, data: dict): ...
def generate_all(processed_dir: Path, manuscript_dir: Path) -> list[Path]: ...
```

Use a single `LABELS = {"id": {...}, "en": {...}}`. Set figure width to `17 / 2.54` inches and save PNG with `dpi=300`. Use Okabe–Ito-compatible colors plus marker/line-shape redundancy. Figure 4 uses ordinary 95% CI from the final ASC model. Figure 5 compares only same-sample models. Figure 6 must not compare coefficients with incompatible units on an unlabelled common magnitude scale; use small multiples or normalized coefficient change with the normalization explicitly labelled.

- [ ] **Step 5: Generate and verify figures**

```bash
python scripts/generate_research_figures.py \
  --processed-dir dataset/survey/processed \
  --manuscript-dir docs/manuscript
python -m unittest tests/test_research_figures.py -v
```

- [ ] **Step 6: Render visual contact sheets for manual inspection**

Use Python/Matplotlib to create temporary contact sheets from all PNGs, inspect for clipped/overlapping labels, and delete the temporary sheets after review. Also parse every SVG using `xml.etree.ElementTree.parse`.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_research_figures.py scripts/requirements.txt tests/test_research_figures.py
git add -f docs/manuscript/id/figures docs/manuscript/en/figures
git commit -m "feat: generate bilingual research figures"
```

---

### Task 5: Draft the Indonesian manuscript

**Files:**
- Create: `docs/manuscript/id/manuscript.md`

**Interfaces:**
- Consumes: spec, template, verified references, audit/model/sensitivity JSON, and Indonesian figures.
- Produces: complete Indonesian anonymous manuscript.

- [ ] **Step 1: Write a failing structural manuscript test**

```python
def test_indonesian_manuscript_structure_and_assets():
    text=ID_MANUSCRIPT.read_text(encoding="utf-8")
    for heading in ("ABSTRAK", "PENDAHULUAN", "METODOLOGI",
                    "HASIL DAN PEMBAHASAN", "KESIMPULAN",
                    "PENGHARGAAN", "PERNYATAAN KEPENTINGAN BERSAING", "REFERENSI"):
        self.assertIn(heading, text)
    self.assertEqual(6, text.count("GAMBAR "))
    self.assertEqual(5, text.count("TABEL "))
    abstract=text.split("ABSTRAK",1)[1].split("Kata kunci:",1)[0]
    self.assertGreaterEqual(len(abstract.split()), 200)
    self.assertLessEqual(len(abstract.split()), 250)
```

- [ ] **Step 2: Run test and verify RED**

```bash
python -m unittest tests/test_manuscripts.py -v
```

Expected: Indonesian manuscript missing.

- [ ] **Step 3: Draft from generated evidence**

Follow the exact approved title and section structure. Include equations, five tables, six figures, limitations, funding placeholders, no author identity, and references in alphabetical order. Every numerical result must be copied from current generated artifacts and cross-checked programmatically.

- [ ] **Step 4: Run Indonesian manuscript checks**

```bash
python -m unittest tests/test_manuscripts.py::ManuscriptTests.test_indonesian_manuscript_structure_and_assets -v
```

If unittest selector syntax is unsupported, run the complete file.

- [ ] **Step 5: Commit**

```bash
git add -f docs/manuscript/id/manuscript.md tests/test_manuscripts.py
git commit -m "docs: draft Indonesian mode choice manuscript"
```

---

### Task 6: Produce the full English manuscript

**Files:**
- Create: `docs/manuscript/en/manuscript.md`
- Modify: `tests/test_manuscripts.py`

**Interfaces:**
- Consumes: Indonesian manuscript and the same generated evidence.
- Produces: complete English manuscript with identical evidence and structure, not a mixed bilingual document.

- [ ] **Step 1: Add failing bilingual consistency tests**

```python
def test_english_manuscript_structure_and_assets():
    text=EN_MANUSCRIPT.read_text(encoding="utf-8")
    for heading in ("ABSTRACT", "INTRODUCTION", "METHODOLOGY",
                    "RESULTS AND DISCUSSION", "CONCLUSION",
                    "ACKNOWLEDGEMENT", "DECLARATION OF COMPETING INTEREST", "REFERENCES"):
        self.assertIn(heading, text)
    self.assertEqual(6, text.count("FIGURE "))
    self.assertEqual(5, text.count("TABLE "))
    abstract=text.split("ABSTRACT",1)[1].split("Keywords:",1)[0]
    self.assertGreaterEqual(len(abstract.split()), 200)
    self.assertLessEqual(len(abstract.split()), 250)


def test_bilingual_manuscripts_share_statistics_and_citations():
    id_text=ID_MANUSCRIPT.read_text(encoding="utf-8")
    en_text=EN_MANUSCRIPT.read_text(encoding="utf-8")
    diagnostics=json.loads(DIAGNOSTICS.read_text())
    for value in manuscript_stat_strings(diagnostics):
        self.assertIn(value, id_text)
        self.assertIn(value, en_text)
    self.assertEqual(extract_citation_keys(id_text), extract_citation_keys(en_text))
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python -m unittest tests/test_manuscripts.py -v
```

Expected: English manuscript missing or consistency failures.

- [ ] **Step 3: Translate academically, preserving evidence**

Translate concepts rather than word-for-word phrasing. Preserve equations, table/figure numbering, all numeric values, citation keys, limitations, and placeholders. Use “on-demand paid transport” or “paid non-public transport” consistently, not generic “ride-hailing.”

- [ ] **Step 4: Run full manuscript checks**

```bash
python -m unittest tests/test_manuscripts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f docs/manuscript/en/manuscript.md tests/test_manuscripts.py
git commit -m "docs: add English mode choice manuscript"
```

---

### Task 7: Final scientific and visual verification

**Files:**
- Modify: `docs/RENCANA_SISTEM.md`
- Modify only if verification finds defects: analysis scripts, figures, or manuscripts.

**Interfaces:**
- Consumes all prior outputs.
- Produces a reproducible, internally consistent submission draft.

- [ ] **Step 1: Run the complete pipeline from source**

```bash
python scripts/run_research_analysis.py \
  --input dataset/choices_long_20260919_112629_diseragamkan.csv \
  --output-dir dataset/survey/processed \
  --manuscript-dir docs/manuscript
```

- [ ] **Step 2: Run all automated checks**

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts src api
python scripts/estimate_mnl.py --demo
git diff --check
```

Expected: zero failures and zero whitespace errors.

- [ ] **Step 3: Verify generated artifact inventory**

```bash
python - <<'PY'
from pathlib import Path
for lang in ('id','en'):
    figures=Path('docs/manuscript')/lang/'figures'
    assert len(list(figures.glob('*.svg'))) == 6
    assert len(list(figures.glob('*.png'))) == 6
    assert (Path('docs/manuscript')/lang/'manuscript.md').exists()
print('artifact inventory OK')
PY
```

- [ ] **Step 4: Perform scientific claim audit**

Read both manuscripts end-to-end and confirm:

- no revealed-preference claim;
- no causal claim;
- no probability-sampling claim;
- no age discussion;
- no author identity;
- no invented ethics/funding metadata;
- low model fit and unexpected coefficient signs are disclosed;
- AIC/BIC are not directly compared across different samples;
- all external claims have verified citations.

- [ ] **Step 5: Update project checkpoint**

Update `docs/RENCANA_SISTEM.md` with the new source checksum, raw/final sample counts, chosen final model, generated manuscript locations, and explicit statement that model deployment remains disabled unless scientific review approves it.

- [ ] **Step 6: Final commit**

```bash
git add scripts tests dataset/survey/processed
git add -f docs/manuscript docs/RENCANA_SISTEM.md
git commit -m "feat: complete bilingual mode choice research package"
```

- [ ] **Step 7: Report exact remaining placeholders**

Report only unresolved submission items, expected to include:

```text
[NAMA PEMBERI DANA]
[NOMOR HIBAH]
[FUNDING AGENCY]
[GRANT NUMBER]
```

Do not call the package submission-ready until those placeholders and author metadata are completed outside the anonymous draft.
