import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class CompareSliderWiringTest(unittest.TestCase):
    def test_map_widget_wiring(self):
        text = read("map_widget.py") + read("assets", "js", "compare_overlay.js")
        for token in ("setCompareMode", "setCompareSide", "setCompareRatio", "CompareSlider"):
            self.assertIn(token, text)
        self.assertIn("compare_slider.js", read("map_widget.py"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "assets", "js", "compare_slider.js")))

    def test_main_wiring(self):
        text = read("main.py")
        for token in ("setCompareMode", "setCompareSide", "Vergleich", "LiDAR-Seite", "Links", "Rechts"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
