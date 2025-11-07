# c4pricing/api/stock_entry.py
import frappe
from frappe import _
from frappe.utils import nowdate, nowtime

@frappe.whitelist()
def create_stock_entry_from_pick_list(pl_name: str):
    """Create Stock Entry (Material Transfer for Manufacture) from Pick List."""
    if not pl_name:
        frappe.throw(_("Pick List name is required"))

    pl = frappe.get_doc("Pick List", pl_name)

    # linked WO
    work_order = getattr(pl, "work_order", None)
    if not work_order:
        for row in pl.get("locations", []) or pl.get("items", []):
            if getattr(row, "work_order", None):
                work_order = row.work_order
                break
    if not work_order:
        frappe.throw(_("This Pick List is not linked to a Work Order"))

    wo = frappe.get_doc("Work Order", work_order)
    if not wo.wip_warehouse:
        frappe.throw(_("Work Order has no WIP Warehouse. Please set it first."))

    company = pl.company or wo.company

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer for Manufacture"
    se.company = company
    se.posting_date = getattr(pl, "posting_date", None) or nowdate()
    se.posting_time = getattr(pl, "posting_time", None) or nowtime()
    se.from_bom = 0
    se.work_order = wo.name
    se.fg_completed_qty = 1
    if "custom_pick_list" in se.meta.get_fieldnames():
        se.custom_pick_list = pl.name
    se.remarks = f"Created from Pick List {pl.name} for Work Order {wo.name}"

    rows = pl.get("locations", []) or pl.get("items", [])
    if not rows:
        frappe.throw(_("Pick List has no rows"))

    for r in rows:
        item_code = getattr(r, "item_code", None)
        qty = getattr(r, "qty", None) or getattr(r, "stock_qty", None) or 0
        s_wh = getattr(r, "warehouse", None) or getattr(r, "s_warehouse", None)

        if not item_code:
            frappe.throw(_("Pick List row is missing Item Code"))

        # لو ما فيش مستودع على السطر، خده من Item Group Defaults (حسب الشركة)
        if not s_wh:
            s_wh = _get_item_group_default_warehouse(item_code, company)

        se.append("items", {
            "item_code": item_code,
            "qty": qty,
            "uom": getattr(r, "uom", None) or _get_stock_uom(item_code),
            "stock_uom": _get_stock_uom(item_code),
            "s_warehouse": s_wh,
            "t_warehouse": wo.wip_warehouse
        })

    se.flags.ignore_permissions = False
    se.insert()
    frappe.db.commit()
    return {"stock_entry": se.name, "message": _("Stock Entry {0} created from Pick List {1}").format(se.name, pl.name)}


@frappe.whitelist()
def get_item_group_default_wh(item_code: str, company: str | None = None):
    """Helper exposed to Client: return Default Warehouse from Item Group Defaults for given company."""
    if not item_code:
        return None
    if not company:
        company = frappe.defaults.get_user_default("Company")
    return _get_item_group_default_warehouse(item_code, company)


def _get_stock_uom(item_code: str) -> str:
    return frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"


def _get_item_group_default_warehouse(item_code: str, company: str | None) -> str | None:
    """Fetch from Item Group Defaults child table by company. Falls back to any row if company not found."""
    ig = frappe.db.get_value("Item", item_code, "item_group")
    if not ig:
        return None

    # حاول باسم الدكتايب الشائع "Item Group Defaults"
    wh = _child_default_wh("Item Group Defaults", ig, company)
    if wh:
        return wh

    # احتياطي لو كان الاسم في إصدارك "Item Group Default"
    wh = _child_default_wh("Item Group Default", ig, company)
    return wh


def _child_default_wh(child_dt: str, parent: str, company: str | None) -> str | None:
    try:
        filters = {"parent": parent}
        if company:
            filters["company"] = company
            rows = frappe.get_all(child_dt, filters=filters, fields=["default_warehouse"], limit=1)
            if rows:
                return rows[0].get("default_warehouse")
        # لو مفيش صف على نفس الشركة، خد أي صف أولي
        rows = frappe.get_all(child_dt, filters={"parent": parent}, fields=["default_warehouse"], limit=1)
        return rows[0].get("default_warehouse") if rows else None
    except Exception:
        return None
