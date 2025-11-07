# c4pricing/overrides/item_flags.py
from __future__ import annotations
import frappe

def _norm(v: str | None) -> str:
    return (v or "").strip().lower()

def enforce_flags_by_item_type(doc, method=None):
    """
    Final guard on server: if custom_item_type matches one of the rules below,
    force the corresponding flags so data is consistent even via imports/API.
    """
    t = _norm(getattr(doc, "custom_item_type", None))
    if not t:
        return

    if t in ("standard product", "customized product"):
        doc.is_purchase_item = 0
        doc.is_sales_item = 1
        doc.is_stock_item = 1
        doc.is_fixed_asset = 0
    elif t in ("material item", "accessories"):
        doc.is_purchase_item = 1
        doc.is_sales_item = 0
        doc.is_stock_item = 1
        doc.is_fixed_asset = 0
    elif t == "asset":
        doc.is_purchase_item = 1
        doc.is_sales_item = 0
        doc.is_stock_item = 0
        doc.is_fixed_asset = 1
    elif t == "service item":
        doc.is_purchase_item = 1
        doc.is_sales_item = 1
        doc.is_stock_item = 0
        doc.is_fixed_asset = 0
    # else: unknown → leave as user set
