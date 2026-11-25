import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.parser import parse_index_ii_text, parse_indian_amount, parse_date_string
from app.automation.selectors import MODE_SELECTORS, COMMON_SELECTORS


class TestIGRParser(unittest.TestCase):
    def test_parse_indian_amount_and_date(self):
        self.assertEqual(parse_indian_amount("Rs. 1,25,000.50"), 125000.50)
        self.assertIsNone(parse_indian_amount(""))
        self.assertEqual(str(parse_date_string("25/11/2026")), "2026-11-25")
        self.assertIsNone(parse_date_string("invalid"))

    def test_parse_index_ii_text_extracts_fields(self):
        sample = """
        Sub-Registrar Office: Haveli 1 Pune
        Document Number: 4521/2024
        Registration Date: 15/06/2024
        Nature of Document: Sale Deed
        Consideration Amount: 45,00,000
        Market Value: 42,50,000
        Seller: Ramesh Kulkarni
        Buyer: Suresh Patil
        Survey No.: 101/2A
        Property Description: Flat No 402, Baner, Pune
        """
        parsed = parse_index_ii_text(sample, row_cells=["4521", "Sale Deed", "15/06/2024"], fallback_year=2024)
        self.assertEqual(parsed["document_number"], "4521/2024")
        self.assertEqual(parsed["sro_name"], "Haveli 1 Pune")
        self.assertEqual(parsed["registration_year"], 2024)
        self.assertEqual(str(parsed["registration_date"]), "2024-06-15")
        self.assertEqual(parsed["article_type"], "Sale Deed")
        self.assertEqual(parsed["consideration_amount"], 4500000.0)
        self.assertEqual(parsed["market_value"], 4250000.0)
        self.assertEqual(parsed["survey_cts_number"], "101/2A")
        self.assertEqual(parsed["party_details"]["seller_or_first_party"], "Ramesh Kulkarni")
        self.assertEqual(parsed["party_details"]["buyer_or_second_party"], "Suresh Patil")

    def test_selectors_cover_all_portal_modes(self):
        for mode in ("PROPERTY_MUMBAI", "PROPERTY_REST_OF_MH", "PROPERTY_URBAN", "DOCUMENT"):
            cfg = MODE_SELECTORS[mode]
            self.assertIn("captcha_img", cfg)
            self.assertIn("captcha_input", cfg)
            self.assertIn("search_btn", cfg)
        self.assertIn("tab_document", COMMON_SELECTORS)
        self.assertIn("results_rows", COMMON_SELECTORS)


if __name__ == "__main__":
    unittest.main()
