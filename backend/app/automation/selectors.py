"""DOM selectors for https://freesearchigrservice.maharashtra.gov.in/."""

COMMON_SELECTORS = {
    "popup": "#popup",
    "popup_close": "button, a, input[type='button'], input[type='submit'], [class*='close'], [id*='close']",
    "update_progress": "[id*='UpdateProgress'], [id*='Progress'], .loading, .loader",
    "tab_property": "#mnuSearchType a:has-text('Property'), a:has-text('Property Details')",
    "tab_document": "#mnuSearchType a:has-text('Document'), a:has-text('Document Number')",
    "region_mumbai": "#btnMumbaisearch",
    "region_rest_of_mh": "#btnOtherdistrictSearch",
    "region_urban": "#btnUrbansearch",
    "results_table": "table[id*='RegistrationGrid'], table[id*='Grid']",
    "results_rows": "table[id*='RegistrationGrid'] tr, table[id*='Grid'] tr",
    "index_ii_link": "input[value*='Index' i], a:has-text('Index'), input[id*='Index' i], button:has-text('Index')",
    "error_labels": "span[id*='lblMsg' i], span[id*='lblError' i], span[id*='lblNoRecord' i], #lblMessage",
}

MODE_SELECTORS = {
    "PROPERTY_MUMBAI": {
        "year_select": "#ddlFromYear",
        "district_select": "#ddlDistrict",
        "area_name_input": "#txtAreaName",
        "village_select": "#ddlareaname",
        "property_input": "#txtAttributeValue",
        "captcha_img": "#imgCaptcha",
        "captcha_input": "#txtImg",
        "search_btn": "#btnSearch",
        "cancel_btn": "#btnCancel",
    },
    "PROPERTY_REST_OF_MH": {
        "year_select": "#ddlFromYear1",
        "district_select": "#ddlDistrict1",
        "tahsil_select": "#ddltahsil",
        "village_select": "#ddlvillage",
        "property_input": "#txtAttributeValue1",
        "captcha_img": "#imgCaptcha_new",
        "captcha_input": "#txtImg1",
        "search_btn": "#btnSearch_RestMaha",
        "cancel_btn": "#btnCancel_RestMaha",
    },
    "DOCUMENT": {
        "doc_type_radios": {
            "efiling": "#rblDocType_0",
            "eregistration": "#rblDocType_1",
            "regular": "#rblDocType_2",
            "isarita": "#rblDocType_3",
            "isarita 2.0": "#rblDocType_3",
        },
        "district_select": "#ddldistrictfordoc",
        "sro_select": "#ddlSROName",
        "year_select": "#ddlYearForDoc",
        "document_input": "#txtDocumentNo",
        "captcha_img": "#imgCaptcha1",
        "captcha_input": "#TextBox1",
        "search_btn": "#btnSearchDoc",
        "cancel_btn": "#btnCancelDoc",
    },
}

# Alias Urban Areas to Rest of Maharashtra form controls (verified identical IDs on portal)
MODE_SELECTORS["PROPERTY_URBAN"] = MODE_SELECTORS["PROPERTY_REST_OF_MH"]
