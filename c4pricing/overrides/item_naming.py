# c4pricing/overrides/item_naming.py
from __future__ import annotations
from c4pricing.api.item_code_rules import next_code

def before_insert_set_code(doc, method=None):
    """If UI didn't set item_code, generate it here; keep name == item_code."""
    if getattr(doc, "item_code", None):
        doc.name = doc.item_code
        return

    item_type = getattr(doc, "custom_item_type", None) or getattr(doc, "item_type", None)
    if not item_type:
        return

    code = next_code(
        item_type=item_type,
        item_group=getattr(doc, "item_group", None),
        brand=getattr(doc, "brand", None),
        main_product=getattr(doc, "custom_main_product", None),
        part_type=getattr(doc, "custom_part_type", None),
        item_name=getattr(doc, "item_name", None),
    )
    if code:
        doc.item_code = code
        doc.name = code
