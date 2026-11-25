SELECTORS = {
    # Region buttons
    "region_mumbai": "#btnMumbaisearch",
    "region_rest_of_mh": "#btnOtherdistrictSearch",
    "region_urban": "#btnUrbansearch",

    # Cascading dropdowns
    "year_select": "#ddlFromYear",
    "district_select": "#ddlDistrict",
    "area_select": "#ddlareaname",

    # Search text inputs
    "area_name_input": "#txtAreaName",
    "attribute_value_input": "#txtAttributeValue",

    # CAPTCHA & Search submit
    "captcha_img": "#imgCaptcha",
    "captcha_input": "#txtImg",
    "search_btn": "#btnSearch",

    # Results table & Index II link (refine once results page is captured)
    "results_rows": "table[id*='Grid'] tr, table.table tr",
    "index_ii_link": "a:has-text('Index'), a:has-text('IndexII'), input[value*='Index']",
}