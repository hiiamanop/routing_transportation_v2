import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from scripts.generate_research_figures import generate_all

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "dataset" / "survey" / "processed"


class ResearchFigureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)

    def test_generates_six_figures_in_two_languages_and_two_formats(self):
        paths = generate_all(PROCESSED, self.output)
        self.assertEqual(24, len(paths))
        for language in ("id", "en"):
            figures = self.output / language / "figures"
            self.assertEqual(6, len(list(figures.glob("*.svg"))))
            self.assertEqual(6, len(list(figures.glob("*.png"))))
            for svg in figures.glob("*.svg"):
                ET.parse(svg)

    def test_png_is_300_dpi_and_approximately_17_cm_wide(self):
        generate_all(PROCESSED, self.output)
        png = next((self.output / "id" / "figures").glob("*.png"))
        with Image.open(png) as image:
            self.assertAlmostEqual(300, image.info["dpi"][0], delta=1)
            self.assertAlmostEqual(2008, image.width, delta=4)

    def test_language_specific_svg_text(self):
        generate_all(PROCESSED, self.output)
        id_svg = (self.output / "id" / "figures" / "figure_02_distribusi_pilihan.svg").read_text()
        en_svg = (self.output / "en" / "figures" / "figure_02_choice_distribution.svg").read_text()
        self.assertIn("Transportasi publik", id_svg)
        self.assertIn("Public transport", en_svg)


if __name__ == "__main__":
    unittest.main()
