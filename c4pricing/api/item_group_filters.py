# c4pricing/api/item_group_filters.py
from __future__ import annotations
import frappe

@frappe.whitelist()
def bounds(parent_group: str):
    """
    Return lft/rgt for a parent Item Group so the client can filter
    all descendants (children + sub-children).
    """
    rec = frappe.db.get_value("Item Group", parent_group, ["lft", "rgt"], as_dict=True)
    if not rec:
        frappe.throw(f"Item Group '{parent_group}' not found.")
    return {"lft": rec.lft, "rgt": rec.rgt}
