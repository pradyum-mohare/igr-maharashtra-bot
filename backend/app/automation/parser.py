"""Parsers and district aliases for normalizing IGR Maharashtra registration data."""

import re
from datetime import date, datetime
from typing import Any


DISTRICT_ALIASES: dict[str, str] = {
    "mumbai": "मुंबई जिल्हा",
    "mumbai city": "मुंबई जिल्हा",
    "mumbai suburban": "मुंबई उपनगर जिल्हा",
    "pune": "पुणे",
    "satara": "सातारा",
    "sangli": "सांगली",
    "kolhapur": "कोल्हापूर",
    "solapur": "सोलापूर",
    "thane": "ठाणे",
    "raigad": "रायगड",
    "sindhudurg": "सिंधुदुर्ग",
    "palghar": "पालघर",
    "nashik": "नाशिक",
    "jalgaon": "जळगाव",
    "dhule": "धुळे",
    "ahilyanagar": "अहिल्यानगर",
    "ahmednagar": "अहिल्यानगर",
    "nandurbar": "नंदुरबार",
    "chhatrapati sambhajinagar": "छत्रपती संभाजीनगर",
    "aurangabad": "छत्रपती संभाजीनगर",
    "jalna": "जालना",
    "beed": "बीड",
    "latur": "लातूर",
    "dharashiv": "धाराशिव",
    "osmanabad": "धाराशिव",
    "nanded": "नांदेड",
    "parbhani": "परभणी",
    "hingoli": "हिंगोली",
    "amravati": "अमरावती",
    "akola": "अकोला",
    "washim": "वाशिम",
    "buldhana": "बुलढाणा",
    "yavatmal": "यवतमाळ",
    "nagpur": "नागपूर",
    "wardha": "वर्धा",
    "bhandara": "भंडारा",
    "gondia": "गोंदिया",
    "chandrapur": "चंद्रपूर",
    "gadchiroli": "गडचिरोली",
    "ratnagiri": "रत्नागिरी",
}


def parse_indian_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", raw)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_date_string(raw: str | None) -> date | None:
    if not raw:
        return None
    text = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _extract_field(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            val = re.sub(r"\s+", " ", match.group(1)).strip(" :-\t\r\n")
            if val:
                return val
    return None


def parse_index_ii_text(
    text: str,
    row_cells: list[str] | None = None,
    fallback_sro: str = "IGR Maharashtra",
    fallback_year: int | None = None,
) -> dict[str, Any]:
    """Extract normalized registration fields from Index-II text and optional summary row cells."""
    cells = [c.strip() for c in (row_cells or []) if c and c.strip()]
    joined_row = " | ".join(cells)

    doc_number = _extract_field(
        text,
        [
            r"(?:Document\s*(?:No\.?|Number)|Doc\.?\s*No\.?|दस्त\s*क्रमांक)\s*[:\-]?\s*([A-Za-z0-9/\-]+)",
        ],
    )
    if not doc_number and cells:
        for cell in cells:
            if re.fullmatch(r"\d{1,8}(?:/\d{4})?", cell):
                doc_number = cell
                break

    sro_name = _extract_field(
        text,
        [
            r"(?:SRO\s*Name|Sub-?Registrar(?:\s*Office)?|दुय्यम\s*निबंधक(?:\s*कार्यालय)?)\s*[:\-]?\s*([^\n\r]+)",
        ],
    ) or fallback_sro

    reg_date_raw = _extract_field(
        text,
        [
            r"(?:Registration\s*Date|Date\s*of\s*Registration|नोंदणी\s*दिनांक)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{2}/\d{2}/\d{4})",
        ],
    )
    reg_date = parse_date_string(reg_date_raw)

    year_val = fallback_year
    if not year_val and reg_date:
        year_val = reg_date.year
    if not year_val:
        year_match = re.search(r"(?:Year|सन)\s*[:\-]?\s*(19\d{2}|20\d{2})", text, re.I)
        year_val = int(year_match.group(1)) if year_match else datetime.utcnow().year

    article_type = _extract_field(
        text,
        [
            r"(?:Document\s*Type|Nature\s*of\s*Document|Article|दस्त\s*प्रकार|दस्ताचा\s*प्रकार)\s*[:\-]?\s*([^\n\r]+)",
        ],
    )

    consideration_raw = _extract_field(
        text,
        [
            r"(?:Consideration(?:\s*Amount)?|मोबदला(?:\s*रक्कम)?)\s*[:\-]?\s*([0-9,]+(?:\.\d+)?)",
        ],
    )
    market_val_raw = _extract_field(
        text,
        [
            r"(?:Market\s*Value|बाजारभाव(?:\s*मूल्य)?)\s*[:\-]?\s*([0-9,]+(?:\.\d+)?)",
        ],
    )

    seller = _extract_field(
        text,
        [
            r"(?:Seller|Party\s*1|First\s*Party|Executant|देणार|लिहून\s*देणार)\s*[:\-]?\s*([^\n\r]+)",
        ],
    )
    buyer = _extract_field(
        text,
        [
            r"(?:Buyer|Purchaser|Party\s*2|Second\s*Party|Claimant|घेणार|लिहून\s*घेणार)\s*[:\-]?\s*([^\n\r]+)",
        ],
    )

    survey_cts = _extract_field(
        text,
        [
            r"(?:Survey\s*No\.?|CTS\s*No\.?|Gat\s*No\.?|Plot\s*No\.?|City\s*Survey\s*No\.?|सर्व्हे\s*नं\.?|गट\s*नं\.?|भूमापन\s*क्रमांक)\s*[:\-]?\s*([^\n\r]+)",
        ],
    )

    property_desc = _extract_field(
        text,
        [
            r"(?:Property\s*Description|Property\s*Details|मिळकतीचे\s*वर्णन|पत्ता)\s*[:\-]?\s*([^\n\r]+(?:\n[^\n\r]+){0,3})",
        ],
    )

    party_details: dict[str, Any] = {}
    if seller:
        party_details["seller_or_first_party"] = seller[:500]
    if buyer:
        party_details["buyer_or_second_party"] = buyer[:500]
    if joined_row:
        party_details["summary_row"] = cells

    return {
        "document_number": (doc_number or f"DOC-{datetime.utcnow().strftime('%H%M%S%f')}")[:100],
        "sro_name": sro_name[:250],
        "registration_year": int(year_val),
        "registration_date": reg_date,
        "article_type": article_type[:250] if article_type else None,
        "consideration_amount": parse_indian_amount(consideration_raw),
        "market_value": parse_indian_amount(market_val_raw),
        "party_details": party_details or None,
        "property_details": (property_desc or text[:4000])[:4000],
        "survey_cts_number": survey_cts[:250] if survey_cts else None,
    }
