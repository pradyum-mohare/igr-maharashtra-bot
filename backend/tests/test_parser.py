import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.parser import (
    OFFICIAL_DISTRICTS,
    devanagari_to_latin,
    match_dropdown_option,
    parse_date_string,
    parse_index_ii_text,
    parse_indian_amount,
)
from app.automation.selectors import COMMON_SELECTORS, MODE_SELECTORS


PORTAL_DOC_DISTRICTS = [
    {"value": "---Select District----", "text": "---Select District----"},
    {"value": "1", "text": "पुणे"},
    {"value": "2", "text": "सातारा"},
    {"value": "3", "text": "सांगली"},
    {"value": "4", "text": "कोल्हापूर"},
    {"value": "5", "text": "सोलापूर"},
    {"value": "6", "text": "ठाणे"},
    {"value": "7", "text": "रायगड"},
    {"value": "8", "text": "रत्नागिरी"},
    {"value": "9", "text": "सिंधुदुर्ग"},
    {"value": "10", "text": "नाशिक"},
    {"value": "11", "text": "जळगाव"},
    {"value": "12", "text": "धुळे"},
    {"value": "13", "text": "अहिल्यानगर"},
    {"value": "14", "text": "छत्रपती संभाजीनगर"},
    {"value": "15", "text": "जालना"},
    {"value": "16", "text": "बीड"},
    {"value": "17", "text": "लातूर"},
    {"value": "18", "text": "नांदेड"},
    {"value": "19", "text": "परभणी"},
    {"value": "20", "text": "धाराशिव"},
    {"value": "21", "text": "अमरावती"},
    {"value": "22", "text": "यवतमाळ"},
    {"value": "23", "text": "अकोला"},
    {"value": "24", "text": "बुलडाणा"},
    {"value": "25", "text": "नागपूर"},
    {"value": "26", "text": "वर्धा"},
    {"value": "27", "text": "चंद्रपूर"},
    {"value": "28", "text": "भंडारा"},
    {"value": "29", "text": "गडचिरोली"},
    {"value": "30", "text": "मुंबई जिल्हा"},
    {"value": "31", "text": "मुंबई उपनगर जिल्हा"},
    {"value": "32", "text": "गोंदिया"},
    {"value": "33", "text": "वाशिम"},
    {"value": "34", "text": "हिंगोली"},
    {"value": "35", "text": "नंदुरबार"},
    {"value": "1001", "text": "महाराष्ट्रातील इतर जिल्हे"},
    {"value": "1002", "text": "महाराष्ट्र सोडून इतर जिल्हे"},
    {"value": "6001", "text": "पालघर"},
]


class TestIGRParser(unittest.TestCase):
    def test_parse_indian_amount_and_date(self):
        self.assertEqual(parse_indian_amount("Rs. 1,25,000.50"), 125000.50)
        self.assertIsNone(parse_indian_amount(""))
        self.assertEqual(str(parse_date_string("25/11/2026")), "2026-11-25")
        self.assertIsNone(parse_date_string("invalid"))

    def test_all_official_districts_match_portal_marathi_options(self):
        for dist in OFFICIAL_DISTRICTS:
            matched = match_dropdown_option(PORTAL_DOC_DISTRICTS, dist["english"])
            self.assertIsNotNone(matched, f"Failed to match {dist}")
            self.assertEqual(matched["text"], dist["marathi"])

        # Alternate English spellings
        for alt, expected in [
            ("Buldana", "बुलडाणा"),
            ("Aurangabad", "छत्रपती संभाजीनगर"),
            ("Ahmednagar", "अहिल्यानगर"),
            ("Osmanabad", "धाराशिव"),
            ("Raigarh", "रायगड"),
            ("Bid", "बीड"),
            ("Gondiya", "गोंदिया"),
        ]:
            matched = match_dropdown_option(PORTAL_DOC_DISTRICTS, alt)
            self.assertIsNotNone(matched, f"Failed alternate spelling {alt}")
            self.assertEqual(matched["text"], expected)

    def test_marathi_tahsil_and_sro_matching(self):
        tahsils = [
            {"value": "1 ", "text": "जुन्नर"},
            {"value": "10", "text": "पुरंदर"},
            {"value": "11", "text": "वेल्हा"},
            {"value": "12", "text": "भोर"},
            {"value": "13", "text": "बारामती"},
            {"value": "14", "text": "ईंदापुर"},
            {"value": "2 ", "text": "आंबेगाव"},
            {"value": "3 ", "text": "शिरुर"},
            {"value": "4 ", "text": "खेड"},
            {"value": "5 ", "text": "हवेली"},
        ]
        for eng, mar in [
            ("Junnar", "जुन्नर"),
            ("Purandar", "पुरंदर"),
            ("Velha", "वेल्हा"),
            ("Bhor", "भोर"),
            ("Baramati", "बारामती"),
            ("Indapur", "ईंदापुर"),
            ("Ambegaon", "आंबेगाव"),
            ("Shirur", "शिरुर"),
            ("Khed", "खेड"),
            ("Haveli", "हवेली"),
        ]:
            matched = match_dropdown_option(tahsils, eng)
            self.assertIsNotNone(matched, f"Failed tahsil {eng} (latin={devanagari_to_latin(mar)})")
            self.assertEqual(matched["text"], mar)

        sros = [
            {"value": "1", "text": "Joint S.R. Haveli 1"},
            {"value": "5", "text": "Joint S.R. Haveli 5"},
            {"value": "15", "text": "Joint S.R. Haveli 15"},
        ]
        matched_sro = match_dropdown_option(sros, "Haveli 5 (Pimpri)")
        self.assertIsNotNone(matched_sro)
        self.assertEqual(matched_sro["value"], "5")

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
