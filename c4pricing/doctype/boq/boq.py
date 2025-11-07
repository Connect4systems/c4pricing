# Copyright (c) 2025, Connect 4 Systems
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


# Which field holds the unit cost in each child table
COST_FIELD_BY_TABLE = {
    "material_costs": "direct_cost",
    "labor_costs": "direct_cost",
    "expenses_table": "cost",
    "contractors_table": "cost",
}


class BOQ(Document):
    """Recalculate child rows and roll-up totals."""

    def validate(self):
        self._recalc_all()

    # ---- internal helpers -------------------------------------------------

    def _recalc_all(self):
        total_material = self._recalc_mat_or_lab(self.get("material_costs"), percent_field="margin")
        total_labor = self._recalc_mat_or_lab(self.get("labor_costs"), percent_field="margin")
        total_expenses = self._recalc_simple(self.get("expenses_table"))
        total_contractors = self._recalc_simple(self.get("contractors_table"))

        self.total_material_costs = total_material
        self.total_labor_costs = total_labor
        self.total_expenses = total_expenses
        self.total_contractors = total_contractors

        self.total_cost = flt(total_material) + flt(total_labor) + flt(total_expenses) + flt(total_contractors)

    @staticmethod
    def _recalc_mat_or_lab(rows, percent_field="margin"):
        """Rows that have direct_cost + margin% -> cost -> total_cost."""
        if not rows:
            return 0.0

        table_sum = 0.0
        for d in rows:
            dc = flt(d.get("direct_cost"))
            margin_pct = flt(d.get(percent_field))
            qty = flt(d.get("qty") or 0)

            cost = dc + (dc * margin_pct / 100.0)
            d.cost = cost
            d.total_cost = cost * qty
            table_sum += d.total_cost

        return table_sum

    @staticmethod
    def _recalc_simple(rows):
        """Rows that have cost only -> total_cost."""
        if not rows:
            return 0.0

        table_sum = 0.0
        for d in rows:
            cost = flt(d.get("cost"))
            qty = flt(d.get("qty") or 0)
            d.total_cost = cost * qty
            table_sum += d.total_cost

        return table_sum


# --------------------- Item Price utilities + Update Costs ---------------------

def _latest_buying_price(item_code: str, price_list: str) -> float:
    """Return latest *buying* Item Price -> price_list_rate (ERPNext v15 fields)."""
    if not item_code:
        return 0.0

    rec = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "price_list": price_list, "buying": 1},
        fields=["price_list_rate", "valid_from", "modified"],
        order_by="valid_from desc, modified desc",
        limit=1,
    )
    if rec:
        return flt(rec[0].get("price_list_rate"))
    return 0.0


@frappe.whitelist()
def update_boq_costs(name: str, price_list: str = "Standard Buying"):
    """
    For each child row:
      - material_costs/labor_costs: set direct_cost from Item Price
      - expenses_table/contractors_table: set cost from Item Price
    Then recompute cost, total_cost, and header totals.
    """
    doc = frappe.get_doc("BOQ", name)
    updated = 0

    # material/labor
    for table in ("material_costs", "labor_costs"):
        for r in doc.get(table) or []:
            if not r.get("item"):
                continue
            r.direct_cost = _latest_buying_price(r.item, price_list)
            updated += 1

    # expenses/contractors
    for table in ("expenses_table", "contractors_table"):
        for r in doc.get(table) or []:
            if not r.get("item"):
                continue
            r.cost = _latest_buying_price(r.item, price_list)
            updated += 1

    # roll-up again and save
    doc._recalc_all()
    doc.save(ignore_permissions=True)

    return {
        "updated_rows": updated,
        "price_list": price_list,
        "new_total_cost": float(doc.total_cost or 0),
    }
