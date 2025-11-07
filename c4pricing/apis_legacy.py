# c4pricing/api.py
from __future__ import annotations

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import today, flt


# ---------- tiny float helper ----------
def _f(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


# ---------- Opportunity -> Costing Note ----------
@frappe.whitelist()
def create_costing_note(source_name: str, target_doc=None, **kwargs):
    def _post(source, target):
        pass

    doc = get_mapped_doc(
        "Opportunity",
        source_name,
        {
            "Opportunity": {
                "doctype": "Costing Note",
                "field_map": {
                    "name": "opportunity",
                    "opportunity_from": "party_type",
                    "party_name": "party_name",
                },
            },
            "Opportunity Item": {
                "doctype": "Costing Note Items",
                "field_map": {"item_code": "item", "qty": "qty"},
            },
        },
        target_doc,
        _post,
    )
    return doc


# ---------- Costing Note row -> BOQ (create or reuse) ----------
@frappe.whitelist()
def create_boq(source_name: str, item_row):
    row = frappe.parse_json(item_row) if isinstance(item_row, (str, bytes)) else (item_row or {})
    row = frappe._dict(row)
    if not row.get("name"):
        frappe.throw("Missing child row id (item_row.name)")

    existing = frappe.db.exists("BOQ", {"costing_note": source_name, "line_id": row.name})
    if existing:
        frappe.db.set_value("Costing Note Items", row.name, "boq_link", existing)
        return {"name": existing}

    def _post(source, target):
        target.naming_series = "BOQ-.YYYY.-"
        target.costing_note = source_name
        target.line_id = row.name
        target.item = row.get("item")
        target.unit = row.get("uom")
        target.project_qty = row.get("qty") or 1
        target.start_date = today()

    doc = get_mapped_doc("Costing Note", source_name, {"Costing Note": {"doctype": "BOQ"}}, None, _post)
    doc.insert(ignore_permissions=True)
    frappe.db.set_value("Costing Note Items", row.name, "boq_link", doc.name)
    return {"name": doc.name}


# ---------- Allow 0 prices in Opportunity items ----------
def opportunity_defaults(doc, method=None):
    for r in getattr(doc, "items", []) or []:
        for f in ("rate", "amount", "base_rate", "base_amount"):
            if r.get(f) is None:
                r.set(f, 0)


# ---------- BOQ -> Costing Note on submit ----------
def push_boq_to_costing_on_submit(doc, method=None):
    """
    When a BOQ is submitted, copy its total_cost back to the linked Costing Note row
    and save the Costing Note.
    """
    if not getattr(doc, "costing_note", None) or not getattr(doc, "line_id", None):
        return

    try:
        cn = frappe.get_doc("Costing Note", doc.costing_note)
    except Exception:
        return

    for row in getattr(cn, "costing_note_items", []):
        if row.name == doc.line_id:
            row.cost = _f(doc.total_cost)
            row.total_cost = _f(row.cost) * _f(row.qty)
            row.boq_link = doc.name
            break

    cn.save(ignore_permissions=True)


# ---------- CN -> Opportunity rates on CN submit (optional) ----------
def update_opportunity_rate_on_cn_submit(doc, method=None):
    if not getattr(doc, "opportunity", None):
        return

    try:
        opp = frappe.get_doc("Opportunity", doc.opportunity)
    except Exception:
        return

    matched = set()
    for cnr in getattr(doc, "costing_note_items", []):
        code = cnr.item
        price = _f(cnr.target_selling_price)

        target = None
        for it in opp.items:
            if it.name in matched:
                continue
            if it.item_code == code:
                target = it
                break

        if not target:
            idx = (cnr.idx or 1) - 1
            if 0 <= idx < len(opp.items):
                target = opp.items[idx]

        if target:
            target.rate = price
            target.base_rate = price
            target.amount = price * _f(target.qty)
            target.base_amount = target.amount
            matched.add(target.name)

    opp.save(ignore_permissions=True)


# ---------- BOQ totals helper (used by "Update Costs" button) ----------
@frappe.whitelist()
def get_boq_totals(boq_name: str):
    """
    Recompute totals from child rows and write them back to the BOQ.
    Returns a dict of totals.
    """
    doc = frappe.get_doc("BOQ", boq_name)

    def row_total(d):
        if getattr(d, "total_cost", None) not in (None, ""):
            return _f(d.total_cost)
        cost = _f(getattr(d, "cost", 0))
        if not cost:
            cost = _f(getattr(d, "direct_cost", 0)) * (1 + _f(getattr(d, "margin", 0)) / 100.0)
        return cost * _f(getattr(d, "qty", 0))

    tm = sum(row_total(d) for d in (doc.material_costs or []))
    tl = sum(row_total(d) for d in (doc.labor_costs or []))
    te = sum(row_total(d) for d in (getattr(doc, "expenses_table", []) or []))
    tc = sum(row_total(d) for d in (getattr(doc, "contractors_table", []) or []))
    total = tm + tl + te + tc

    doc.total_material_costs = tm
    doc.total_labor_costs = tl
    doc.total_expenses = te
    doc.total_contractors = tc
    doc.total_cost = total
    doc.save(ignore_permissions=True)

    return {
        "total_material_costs": tm,
        "total_labor_costs": tl,
        "total_expenses": te,
        "total_contractors": tc,
        "total_cost": total,
    }


# ---------- Opportunity -> Quotation (merge standard + custom table) ----------
@frappe.whitelist()
def make_quotation_with_standard(source_name: str, target_doc=None):
    """
    Create a Quotation from Opportunity, then append rows from the custom
    child table 'custom_standard' (DocType: 'Standard Product').

    - Opportunity.items (core)              -> handled by ERPNext mapper
    - Opportunity.custom_standard (table)   -> appended here to Quotation.items
    """
    # 1) call ERPNext’s original mapper first to bring core Opportunity Items
    from erpnext.crm.doctype.opportunity.opportunity import make_quotation as _core_make_quotation

    qtn = _core_make_quotation(source_name, target_doc=target_doc)

    # 2) append our custom table rows
    opp = frappe.get_doc("Opportunity", source_name)
    custom_rows = getattr(opp, "custom_standard", None) or []  # fieldname on Opportunity

    for r in custom_rows:
        # Quotation Item fields; extend if you have custom ones on your site
        qty = flt(r.get("qty"))
        rate = flt(r.get("rate"))
        amount = flt(r.get("amount")) if r.get("amount") not in (None, "") else qty * rate

        qtn.append("items", {
            "item_code": r.get("item"),
            "item_name": r.get("item_name"),
            "description": r.get("description"),
            "uom": r.get("uom"),
            "conversion_factor": 1,
            "qty": qty,
            "rate": rate,
            "amount": amount,
        })

    # Ensure totals/taxes are consistent
    qtn.flags.ignore_permissions = True
    qtn.run_method("set_missing_values")
    qtn.calculate_taxes_and_totals()

    return qtn
