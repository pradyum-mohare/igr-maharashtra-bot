"""Parsers, district aliases, and Marathi/English dropdown matching for IGR Maharashtra."""

import re
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any


OFFICIAL_DISTRICTS: list[dict[str, str]] = [
    {"english": "Mumbai City", "marathi": "मुंबई जिल्हा"},
    {"english": "Mumbai Suburban", "marathi": "मुंबई उपनगर जिल्हा"},
    {"english": "Pune", "marathi": "पुणे"},
    {"english": "Thane", "marathi": "ठाणे"},
    {"english": "Palghar", "marathi": "पालघर"},
    {"english": "Raigad", "marathi": "रायगड"},
    {"english": "Ratnagiri", "marathi": "रत्नागिरी"},
    {"english": "Sindhudurg", "marathi": "सिंधुदुर्ग"},
    {"english": "Nashik", "marathi": "नाशिक"},
    {"english": "Ahilyanagar (Ahmednagar)", "marathi": "अहिल्यानगर"},
    {"english": "Dhule", "marathi": "धुळे"},
    {"english": "Nandurbar", "marathi": "नंदुरबार"},
    {"english": "Jalgaon", "marathi": "जळगाव"},
    {"english": "Satara", "marathi": "सातारा"},
    {"english": "Sangli", "marathi": "सांगली"},
    {"english": "Kolhapur", "marathi": "कोल्हापूर"},
    {"english": "Solapur", "marathi": "सोलापूर"},
    {"english": "Chhatrapati Sambhajinagar (Aurangabad)", "marathi": "छत्रपती संभाजीनगर"},
    {"english": "Jalna", "marathi": "जालना"},
    {"english": "Beed", "marathi": "बीड"},
    {"english": "Latur", "marathi": "लातूर"},
    {"english": "Dharashiv (Osmanabad)", "marathi": "धाराशिव"},
    {"english": "Nanded", "marathi": "नांदेड"},
    {"english": "Parbhani", "marathi": "परभणी"},
    {"english": "Hingoli", "marathi": "हिंगोली"},
    {"english": "Amravati", "marathi": "अमरावती"},
    {"english": "Akola", "marathi": "अकोला"},
    {"english": "Washim", "marathi": "वाशिम"},
    {"english": "Buldhana", "marathi": "बुलडाणा"},
    {"english": "Yavatmal", "marathi": "यवतमाळ"},
    {"english": "Nagpur", "marathi": "नागपूर"},
    {"english": "Wardha", "marathi": "वर्धा"},
    {"english": "Bhandara", "marathi": "भंडारा"},
    {"english": "Gondia", "marathi": "गोंदिया"},
    {"english": "Chandrapur", "marathi": "चंद्रपूर"},
    {"english": "Gadchiroli", "marathi": "गडचिरोली"},
    {"english": "Other Districts in Maharashtra", "marathi": "महाराष्ट्रातील इतर जिल्हे"},
    {"english": "Outside Maharashtra", "marathi": "महाराष्ट्र सोडून इतर जिल्हे"},
]

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
    "raigarh": "रायगड",
    "ratnagiri": "रत्नागिरी",
    "sindhudurg": "सिंधुदुर्ग",
    "palghar": "पालघर",
    "nashik": "नाशिक",
    "jalgaon": "जळगाव",
    "dhule": "धुळे",
    "ahilyanagar": "अहिल्यानगर",
    "ahmednagar": "अहिल्यानगर",
    "ahilyanagar (ahmednagar)": "अहिल्यानगर",
    "nandurbar": "नंदुरबार",
    "chhatrapati sambhajinagar": "छत्रपती संभाजीनगर",
    "sambhajinagar": "छत्रपती संभाजीनगर",
    "aurangabad": "छत्रपती संभाजीनगर",
    "chhatrapati sambhajinagar (aurangabad)": "छत्रपती संभाजीनगर",
    "jalna": "जालना",
    "beed": "बीड",
    "bid": "बीड",
    "latur": "लातूर",
    "dharashiv": "धाराशिव",
    "osmanabad": "धाराशिव",
    "dharashiv (osmanabad)": "धाराशिव",
    "nanded": "नांदेड",
    "parbhani": "परभणी",
    "hingoli": "हिंगोली",
    "amravati": "अमरावती",
    "akola": "अकोला",
    "washim": "वाशिम",
    "buldhana": "बुलडाणा",
    "buldana": "बुलडाणा",
    "yavatmal": "यवतमाळ",
    "nagpur": "नागपूर",
    "wardha": "वर्धा",
    "bhandara": "भंडारा",
    "gondia": "गोंदिया",
    "gondiya": "गोंदिया",
    "chandrapur": "चंद्रपूर",
    "gadchiroli": "गडचिरोली",
    "other districts in maharashtra": "महाराष्ट्रातील इतर जिल्हे",
    "outside maharashtra": "महाराष्ट्र सोडून इतर जिल्हे",
}

_DEV_CONSONANTS: dict[str, str] = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "ळ": "l",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}

_DEV_INDEP_VOWELS: dict[str, str] = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "अं": "am", "ऑ": "o",
}

_DEV_MATRAS: dict[str, str] = {
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "a",
}


def devanagari_to_latin(text: str) -> str:
    """Convert Marathi Devanagari text to approximate phonetic Latin for dropdown matching."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch in _DEV_CONSONANTS:
            base = _DEV_CONSONANTS[ch]
            if nxt == "्":  # virama suppresses inherent 'a'
                out.append(base)
                i += 2
                continue
            if nxt in _DEV_MATRAS:
                out.append(base + _DEV_MATRAS[nxt])
                i += 2
                continue
            # Inherent 'a' unless end of word
            is_word_end = not nxt or not ("\u0900" <= nxt <= "\u097f")
            out.append(base if is_word_end else base + "a")
            i += 1
        elif ch in _DEV_INDEP_VOWELS:
            out.append(_DEV_INDEP_VOWELS[ch])
            i += 1
        elif ch in _DEV_MATRAS:
            out.append(_DEV_MATRAS[ch])
            i += 1
        elif ch in ("ं", "ँ"):
            out.append("n")
            i += 1
        elif ch == "ः":
            out.append("h")
            i += 1
        elif "०" <= ch <= "९":
            out.append(chr(ord("0") + ord(ch) - ord("०")))
            i += 1
        else:
            out.append(ch.lower())
            i += 1
    return "".join(out)


def _normalize_latin(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.replace("gaon", "gav").replace("nb", "mb").replace("np", "mp")
    s = s.replace("w", "v").replace("ee", "i").replace("oo", "u").replace("ph", "f")
    return re.sub(r"\s+", " ", s).strip()


def match_dropdown_option(options: list[dict[str, str]], query: str) -> dict[str, str] | None:
    """Match user query (English, Marathi, or alias) against dropdown {value, text} options."""
    raw = query.strip()
    if not raw:
        return None
    norm_raw = raw.lower()
    stripped_raw = re.sub(r"\([^)]*\)", " ", norm_raw)
    stripped_raw = re.sub(r"\s+", " ", stripped_raw).strip()

    alias = DISTRICT_ALIASES.get(norm_raw) or DISTRICT_ALIASES.get(stripped_raw)

    valid = [
        opt for opt in options
        if opt.get("value")
        and opt["value"] not in {"0", "-1"}
        and not opt.get("text", "").strip().startswith("---")
    ]

    # 1. Exact value / text / alias match
    for opt in valid:
        txt = opt["text"].strip()
        val = opt["value"].strip()
        if txt.lower() == norm_raw or val.lower() == norm_raw or (alias and txt == alias):
            return opt

    # 2. Substring match on text or alias (handles "Pune" -> "पुणे", "Haveli 5 (Pimpri)" -> "Joint S.R. Haveli 5")
    for opt in valid:
        txt = opt["text"].strip()
        low = txt.lower()
        if (alias and alias in txt) or norm_raw in low or (stripped_raw and stripped_raw in low):
            return opt

    # 3. Whole-token match (handles "Haveli 5 (Pimpri)" -> "Joint S.R. Haveli 5" without matching "15")
    raw_tokens = [t for t in re.split(r"[^a-z0-9\u0900-\u097f]+", stripped_raw) if t]
    if raw_tokens:
        for opt in valid:
            txt = opt["text"].strip()
            opt_tokens = [t for t in re.split(r"[^a-z0-9\u0900-\u097f]+", txt.lower()) if t]
            if all(t in opt_tokens for t in raw_tokens):
                return opt

    # 4. Devanagari-to-Latin phonetic match (handles English Tahsil/Village vs Marathi dropdowns)
    norm_q = _normalize_latin(raw)
    best_opt = None
    best_score = 0.0
    for opt in valid:
        txt = opt["text"].strip()
        latin_opt = _normalize_latin(devanagari_to_latin(txt))
        if not latin_opt:
            continue
        if norm_q == latin_opt or norm_q in latin_opt or latin_opt in norm_q:
            return opt
        score = SequenceMatcher(None, norm_q, latin_opt).ratio()
        if score > best_score:
            best_score = score
            best_opt = opt

    if best_opt and best_score >= 0.72:
        return best_opt
    return None


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
