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
        self.assertIn("Transportasi Publik", id_svg)
        self.assertIn("Public Transport", en_svg)

    def test_revised_figures_are_spacious_directly_labelled_and_have_no_patterns(self):
        generate_all(PROCESSED, self.output)
        for language in ("id", "en"):
            figures = self.output / language / "figures"
            for svg in figures.glob("*.svg"):
                self.assertNotIn("<pattern", svg.read_text(), svg.name)

        with Image.open(self.output / "en" / "figures" / "figure_01_research_flow.png") as image:
            self.assertGreaterEqual(image.height, 1400)

        coefficients = (self.output / "en" / "figures" / "figure_04_mnl_coefficients.svg").read_text()
        model_fit = (self.output / "en" / "figures" / "figure_05_model_fit.svg").read_text()
        stability = (self.output / "en" / "figures" / "figure_06_coefficient_stability.svg").read_text()
        self.assertIn("Standardised Coefficient", coefficients)
        self.assertIn("518.10", model_fit)
        self.assertIn("Travel Time", stability)


if __name__ == "__main__":
    unittest.main()
