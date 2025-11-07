# Copyright (c) 2025, Connect 4 Systems
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CostingNote(Document):
    """
    Costing Note logic:
    - validate:
        * per-row: target_selling_price = cost + (cost * margin/100)
                   total_cost          = cost * qty
                   total_selling       = target_selling_price * qty
        * header:  total_cost = Σ row.total_cost
                   total_target_selling_price = Σ row.total_selling
                   total_profit = total_target_selling_price - total_cost
                   profit_margin = total_profit / total_cost   (0 if total_cost = 0)
    - on_submit: push target_selling_price to linked Opportunity items
    """

    # ---------------- lifecycle ----------------
    def validate(self):
        self._update_target_selling_prices()
        self._rollup_totals()

    def on_submit(self):
        self._push_to_opportunity()

    # ---------------- helpers ----------------
    def _row_margin(self, row) -> float:
        """
        Margin precedence:
          1) row.default_profit_margin (your current model)
          2) self.default_profit_margin (if you add a parent field later)
          3) self.profit_margin (existing parent field)
        """
        return flt(
            row.get("default_profit_margin", None)
            or getattr(self, "default_profit_margin", None)
            or getattr(self, "profit_margin", 0)
        )

    def _update_target_selling_prices(self):
        """target_selling_price = cost + (cost * (margin / 100))."""
        for row in (self.get("costing_note_items") or []):
            cost = flt(row.get("cost"))
            if not cost:
                row.target_selling_price = 0.0
                continue
            margin = self._row_margin(row)
            row.target_selling_price = cost + (cost * margin / 100.0)

    def _rollup_totals(self):
        """Compute per-row totals and roll them up to the parent."""
        total_cost_sum = 0.0
        total_sell_sum = 0.0

        for row in (self.get("costing_note_items") or []):
            qty = flt(row.get("qty"))
            cost = flt(row.get("cost"))
            tsp  = flt(row.get("target_selling_price"))

            # per-row totals
            row.total_cost = cost * qty
            # If child field total_selling exists, this will be saved; if not, harmless.
            row.total_selling = tsp * qty

            total_cost_sum += flt(row.total_cost)
            total_sell_sum += tsp * qty

        # write header totals
        self.total_cost = total_cost_sum
        self.total_target_selling_price = total_sell_sum
        self.total_profit = flt(self.total_target_selling_price) - flt(self.total_cost)
        self.profit_margin = (self.total_profit / self.total_cost) if flt(self.total_cost) else 0.0

    def _push_to_opportunity(self):
        """On submit → push Opportunity Item rates from target_selling_price."""
        if not getattr(self, "opportunity", None):
            return

        opp = frappe.get_doc("Opportunity", self.opportunity)
        if not getattr(opp, "items", None):
            return

        rate_by_item = {
            row.get("item"): flt(row.get("target_selling_price"))
            for row in (self.get("costing_note_items") or [])
            if row.get("item")
        }

        changed = False
        for it in opp.items:
            if it.item_code in rate_by_item:
                new_rate = rate_by_item[it.item_code]
                if flt(it.rate) != new_rate:
                    it.rate = new_rate
                    it.base_rate = new_rate
                    it.amount = new_rate * flt(it.qty or 0)
                    it.base_amount = it.amount
                    changed = True

        if changed:
            opp.flags.ignore_permissions = True
            opp.save()
