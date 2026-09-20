import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID = ROOT / "docs" / "manuscript" / "id" / "manuscript.md"
EN = ROOT / "docs" / "manuscript" / "en" / "manuscript.md"


class ManuscriptTests(unittest.TestCase):
    def test_indonesian_manuscript_structure_and_assets(self):
        text = ID.read_text(encoding="utf-8")
        for heading in ("ABSTRAK", "PENDAHULUAN", "METODOLOGI", "HASIL DAN PEMBAHASAN",
                        "KESIMPULAN", "PENGHARGAAN", "PERNYATAAN KEPENTINGAN BERSAING", "REFERENSI"):
            self.assertIn(heading, text)
        self.assertEqual(6, len(re.findall(r"^GAMBAR \d+\.", text, re.MULTILINE)))
        self.assertEqual(5, len(re.findall(r"^TABEL \d+\.", text, re.MULTILINE)))
        abstract = text.split("ABSTRAK", 1)[1].split("Kata kunci:", 1)[0]
        self.assertGreaterEqual(len(abstract.split()), 200)
        self.assertLessEqual(len(abstract.split()), 250)

    def test_english_manuscript_structure_and_assets(self):
        text = EN.read_text(encoding="utf-8")
        for heading in ("ABSTRACT", "INTRODUCTION", "METHODOLOGY", "RESULTS AND DISCUSSION",
                        "CONCLUSION", "ACKNOWLEDGEMENT", "DECLARATION OF COMPETING INTEREST", "REFERENCES"):
            self.assertIn(heading, text)
        self.assertEqual(6, len(re.findall(r"^FIGURE \d+\.", text, re.MULTILINE)))
        self.assertEqual(5, len(re.findall(r"^TABLE \d+\.", text, re.MULTILINE)))
        abstract = text.split("ABSTRACT", 1)[1].split("Keywords:", 1)[0]
        self.assertGreaterEqual(len(abstract.split()), 200)
        self.assertLessEqual(len(abstract.split()), 250)

    def test_bilingual_manuscripts_share_core_statistics(self):
        id_text, en_text = ID.read_text(), EN.read_text()
        for value in ("400", "318", "0.0514", "0.610", "0.0132", "0.3790"):
            self.assertIn(value, id_text)
            self.assertIn(value, en_text)
        self.assertNotRegex(id_text + en_text, r"(?i)revealed preference")


if __name__ == "__main__":
    unittest.main()
