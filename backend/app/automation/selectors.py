# Update these IDs/selectors after inspecting freesearchigrservice.maharashtra.gov.in
# Tip: ASP.NET WebForms IDs often end with $ddlYear, $ddlDistrict, $txtCaptcha, etc.
SELECTORS = {
    # Region / Tab buttons or radios (e.g., Mumbai, Rest of Maharashtra, Urban Areas)
    "region_rest_of_mh": "input[id*='RestOfMaharashtra'], a:has-text('Rest of Maharashtra')",
    "region_mumbai": "input[id*='Mumbai'], a:has-text('Mumbai')",
    "region_urban": "input[id*='Urban'], a:has-text('Urban')",

    # Search mode toggles (Property Details vs Document Number)
    "mode_property": "input[id*='Property'], label:has-text('Property')",
    "mode_document": "input[id*='Document'], label:has-text('Document')",

    # Common cascading dropdowns & inputs
    "year_select": "select[id*='Year'], select[id*='ddlYear']",
    "district_select": "select[id*='District'], select[id*='ddlDistrict']",
    "sro_select": "select[id*='SRO'], select[id*='ddlSRO'], select[id*='Office']",
    "village_input": "input[id*='Village'], input[id*='txtVillage']",
    "village_select": "select[id*='Village'], select[id*='ddlVillage']",
    "property_no_input": "input[id*='PropertyNo'], input[id*='SurveyNo'], input[id*='txtProperty']",
    "doc_no_input": "input[id*='DocNo'], input[id*='DocumentNo'], input[id*='txtDocument']",

    # CAPTCHA & Search button
    "captcha_img": "img[id*='Captcha'], img[id*='captcha']",
    "captcha_input": "input[id*='Captcha'], input[id*='captcha']",
    "search_btn": "input[type='submit'][value*='Search'], button:has-text('Search'), a:has-text('Search')",

    # Results table & Index II link
    "results_rows": "table[id*='Grid'] tr, table.table tr",
    "index_ii_link": "a:has-text('Index'), a:has-text('IndexII'), input[value*='Index']",
}