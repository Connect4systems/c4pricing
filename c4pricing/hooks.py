app_name = "c4pricing"
app_title = "c4pricing"
app_publisher = "connect4systems"
app_description = "c4pricing"
app_email = "info@connect4systems"
app_license = "mit"

doctype_js = {
    "Opportunity": "public/js/doctype/opportunity.js",
    "Costing Note": "c4pricing/doctype/costing_note/costing_note.js",
    "BOQ": "c4pricing/doctype/boq/boq.js",
    # ONE entry for Item so the code surely loads
    "Item": "public/js/doctype/item_autocode.js",
    "Pick List": "public/js/doctype/pick_list.js",
}

doc_events = {
    "Opportunity": {
        "validate": "c4pricing.api.opportunity_defaults",
    },
    "BOQ": {
        "on_submit": "c4pricing.api.push_boq_to_costing_on_submit",
    },
    "Costing Note": {
        "on_submit": "c4pricing.api.update_opportunity_rate_on_cn_submit",
    },
    "Item": {
        "before_insert": "c4pricing.overrides.item_naming.before_insert_set_code",
        
        # (optional) keep your flags enforcer if you use it:
        # "validate": "c4pricing.overrides.item_flags.enforce_flags_by_item_type",
    },
}

override_whitelisted_methods = {
    "erpnext.crm.doctype.opportunity.opportunity.make_quotation": "c4pricing.api.make_quotation_with_standard",
}

fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "in", ["Stock Entry"]]]}
]