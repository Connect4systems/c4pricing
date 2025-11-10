# Copyright (c) 2025, Connect 4 Systems
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CostingNote(Document):
    """On submit → push Opportunity Item rate from target_selling_price."""

    def on_submit(self):
        if not self.opportunity:
            return

        opp = frappe.get_doc("Opportunity", self.opportunity)
        if not getattr(opp, "items", None):
            return

        # Map by item code
        rate_by_item = {}
        for row in self.get("costing_note_items") or []:
            item_code = row.get("item")
            if not item_code:
                continue
            rate_by_item[item_code] = flt(row.get("target_selling_price"))

        changed = False
        for it in opp.items:
            if it.item_code in rate_by_item:
                new_rate = rate_by_item[it.item_code]
                if flt(it.rate) != new_rate:
                    it.rate = new_rate
                    it.base_rate = new_rate  # keep in sync
                    it.amount = new_rate * flt(it.qty or 0)
                    it.base_amount = it.amount
                    changed = True

        if changed:
            opp.flags.ignore_permissions = True
            opp.save()
