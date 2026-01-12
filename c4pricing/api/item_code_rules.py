# c4pricing/api/item_code_rules.py
from __future__ import annotations
import re
import frappe
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime

def _norm(v: str | None) -> str:
    return (v or "").strip().lower()

def _slug(v: str | None) -> str:
    s = (v or "").upper().strip().replace(" ", "-")
    return re.sub(r"[^A-Z0-9\-]", "", s)

def _brand_abr(brand: str | None) -> str:
    return ((brand and frappe.db.get_value("Brand", brand, "custom_abr")) or "").strip().upper()

def _group_abr(item_group: str | None) -> str:
    return ((item_group and frappe.db.get_value("Item Group", item_group, "custom_abr")) or "").strip().upper()

def _type_abr(item_type: str | None) -> str:
    return ((item_type and frappe.db.get_value("Item Type", item_type, "abr")) or "").strip().upper()

def _main_code(main_item: str | None) -> str:
    if not main_item:
        return ""
    code = frappe.db.get_value("Item", main_item, "item_code") or main_item
    return _slug(code)

def _unique_code(base: str, width: int = 3) -> str:
    if not frappe.db.exists("Item", base):
        return base
    for i in range(1, 1000):
        candidate = f"{base}-{i:0{width}d}"
        if not frappe.db.exists("Item", candidate):
            return candidate
    frappe.throw("Unable to generate unique code. Please revise naming rule.")

@frappe.whitelist()
def next_code(
    item_type: str,
    item_group: str | None = None,
    brand: str | None = None,
    main_product: str | None = None,
    part_type: str | None = None,
    item_name: str | None = None,
) -> str:
    """
    Naming rules:
      - Standard Product     : {Brand.custom_abr}-{ItemGroup.custom_abr}-###
      - Asset Item           : AS-{ItemGroup.custom_abr}-###
      - Accessories          : ACS-####
      - Services             : SRV-###
      - Material Item        : MTR-{ItemGroup.custom_abr}-###
      - Customized Product   : {ItemType.abr}-{ItemGroup.custom_abr}-###
      - Part                 : PRT-(custom_main_product)-(custom_part_type)  [unique if needed]
      - WIP                  : WIP-(custom_main_product)-item_name           [unique if needed]
    """
    t = _norm(item_type)

    # Standard Product → Brand + Group
    if t == "standard product":
        b = _brand_abr(brand)
        g = _group_abr(item_group)
        if not b:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Brand</b>.")
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"{b}-{g}-.###")

    # Asset Item → AS-{Group}-###
    if t in ("asset item", "asset"):
        g = _group_abr(item_group)
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"AS-{g}-.###")

    # Accessories → ACS-####
    if t == "accessories":
        return make_autoname("ACS-.####")

    # Services → SRV-###
    if t == "services":
        return make_autoname("SRV-.###")

    # Part → PRT-(main_product)-(part_type) with uniqueness
    if t == "part":
        mp = _main_code(main_product)
        pt = _slug(part_type)
        if not mp:
            frappe.throw("Please select <b>Main Product</b> (field: custom_main_product).")
        if not pt:
            frappe.throw("Please set <b>Part Type</b> (field: custom_part_type).")
        base = f"PRT-{mp}-{pt}"
        return _unique_code(base, width=3)

    # WIP → WIP-(main_product)-item_name with uniqueness
    if t == "wip":
        mp = _main_code(main_product)
        nm = _slug(item_name)
        if not mp:
            frappe.throw("Please select <b>Main Product</b> (field: custom_main_product).")
        if not nm:
            frappe.throw("Please set <b>Item Name</b>.")
        base = f"WIP-{mp}-{nm}"
        return _unique_code(base, width=3)

    # Material Item → MTR-{Group}-###
    if t == "material item":
        g = _group_abr(item_group)
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"MTR-{g}-.###")

    # Customized Product → {Type.abr}-{Group}-###
    if t == "customized product":
        ta = _type_abr(item_type)
        g  = _group_abr(item_group)
        if not ta:
            frappe.throw("Please set <b>abr</b> on the selected <b>Item Type</b>.")
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"{ta}-{g}-.###")

    frappe.throw(f"No naming rule defined for Item Type: <b>{item_type}</b>")
