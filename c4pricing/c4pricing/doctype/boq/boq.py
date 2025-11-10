# Copyright (c) 2025, Connect 4 Systems
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt

# ---------------------- Core BOQ recalculation ----------------------

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
        # If header margins changed, sync them to all rows (non-ambiguous, per your spec)
        self._sync_row_margins_if_header_changed()
        # Always recompute totals
        self._recalc_all()

    # ---- internal helpers -------------------------------------------------

    def _sync_row_margins_if_header_changed(self):
        """
        Force-propagate margins to ALL rows ONLY when header changed since last save.
          - New doc OR base_margin changed  -> set all material_costs.margin = base_margin
          - New doc OR s_margin changed     -> set all labor_costs.margin    = s_margin
        Otherwise keep user-edited margins intact.
        """
        prev_base = prev_s = None
        base = flt(getattr(self, "base_margin", 0))
        s    = flt(getattr(self, "s_margin", 0))

        if self.name and frappe.db.exists("BOQ", self.name):
            prev = frappe.db.get_value("BOQ", self.name, ["base_margin", "s_margin"], as_dict=True)
            if prev:
                prev_base = flt(prev.get("base_margin"))
                prev_s    = flt(prev.get("s_margin"))

        base_changed = (prev_base is None) or (flt(prev_base) != base)
        s_changed    = (prev_s is None) or (flt(prev_s) != s)

        if base_changed:
            for d in (self.get("material_costs") or []):
                d.margin = base

        if s_changed:
            for d in (self.get("labor_costs") or []):
                d.margin = s

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


# --------------------- Cost source utilities ---------------------

def _latest_buying_price(item_code: str, price_list: str) -> float:
    """Return latest *buying* Item Price from the given Price List."""
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


def _valuation_rate(item_code: str, warehouse: str | None = None, company: str | None = None) -> float:
    """Get a reasonable valuation rate for the item (Bin / SLE / ERPNext stock utils)."""
    if not item_code:
        return 0.0

    # Preferred: ERPNext stock utils
    try:
        from erpnext.stock.utils import get_valuation_rate
        rate = get_valuation_rate(
            item_code=item_code,
            warehouse=warehouse,
            company=company,
            qty=0,
            rate=0,
            voucher_type=None,
            voucher_no=None,
        ) or 0
        if rate:
            return flt(rate)
    except Exception:
        pass

    # Fallback A: latest Bin valuation_rate
    try:
        bin_filters = {"item_code": item_code}
        if warehouse:
            bin_filters["warehouse"] = warehouse
        rec = frappe.get_all(
            "Bin",
            filters=bin_filters,
            fields=["valuation_rate"],
            order_by="modified desc",
            limit=1,
        )
        if rec and rec[0].get("valuation_rate"):
            return flt(rec[0]["valuation_rate"])
    except Exception:
        pass

    # Fallback B: last SLE with a valuation_rate
    try:
        sle_filters = {"item_code": item_code}
        if warehouse:
            sle_filters["warehouse"] = warehouse
        rec = frappe.get_all(
            "Stock Ledger Entry",
            filters=sle_filters,
            fields=["valuation_rate"],
            order_by="posting_date desc, posting_time desc, creation desc",
            limit=1,
        )
        if rec and rec[0].get("valuation_rate"):
            return flt(rec[0]["valuation_rate"])
    except Exception:
        pass

    return 0.0


def _last_purchase_rate(item_code: str) -> float:
    """Return last purchase rate from Purchase Invoice Item or Purchase Receipt Item."""
    if not item_code:
        return 0.0

    rec = frappe.get_all(
        "Purchase Invoice Item",
        filters={"item_code": item_code},
        fields=["rate"],
        order_by="creation desc",
        limit=1,
    )
    if rec and rec[0].get("rate"):
        return flt(rec[0].rate)

    rec = frappe.get_all(
        "Purchase Receipt Item",
        filters={"item_code": item_code},
        fields=["rate"],
        order_by="creation desc",
        limit=1,
    )
    if rec and rec[0].get("rate"):
        return flt(rec[0].rate)

    return 0.0


# --------------------- Update Costs ---------------------

@frappe.whitelist()
def update_boq_costs(
    name: str,
    source: str = "price_list",
    price_list: str = "Standard Buying",
    warehouse: str | None = None,
    company: str | None = None,
):
    """
    Update BOQ child rows' unit cost using one of three sources:
      - price_list   : Item Price (buying) from the given price_list
      - valuation    : latest valuation rate
      - last_purchase: last purchase rate from Purchase Invoice/Receipt

    Then recompute row totals and header totals (margins already synced on validate).
    """
    if source not in ("price_list", "valuation", "last_purchase"):
        source = "price_list"

    doc = frappe.get_doc("BOQ", name)
    updated = 0

    def set_row_cost(row, target_field: str):
        nonlocal updated
        if not row.get("item"):
            return

        if source == "price_list":
            val = _latest_buying_price(row.item, price_list)
        elif source == "valuation":
            val = _valuation_rate(row.item, warehouse=warehouse, company=company)
        elif source == "last_purchase":
            val = _last_purchase_rate(row.item)
        else:
            val = 0

        row.set(target_field, val)
        updated += 1

    # material/labor → direct_cost
    for table in ("material_costs", "labor_costs"):
        for r in doc.get(table) or []:
            set_row_cost(r, "direct_cost")

    # expenses/contractors → cost
    for table in ("expenses_table", "contractors_table"):
        for r in doc.get(table) or []:
            set_row_cost(r, "cost")

    # Recompute totals; margins will be enforced on next validate if headers change
    doc._recalc_all()
    doc.save(ignore_permissions=True)

    return {
        "updated_rows": updated,
        "source": source,
        "price_list": price_list,
        "warehouse": warehouse,
        "company": company,
        "new_total_cost": float(doc.total_cost or 0),
    }
