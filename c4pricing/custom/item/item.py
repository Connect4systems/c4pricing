import frappe
from frappe.model.document import Document

def calculate_item_totals(doc, method):
    width = float(doc.custom_width or 0)
    height = float(doc.custom_hight or 0)  # ← تم التصحيح هنا
    depth = float(doc.custom_depth or 0)
    measurement_type = doc.custom_measurement_type

    total = 0

    if measurement_type == "Area":
        total = width * height
    elif measurement_type == "Perimeter":
        total = 2 * (width + height)
    elif measurement_type == "Depth":
        total = width * height * depth
    elif measurement_type == "Width Only":
        total = width
    elif measurement_type == "Height Only":
        total = height

    doc.custom_total = total

    # Fetch conversion factor from UOM Conversion child table
    conversion_factor = 1
    for row in doc.uoms:
        if row.uom == doc.stock_uom:
            conversion_factor = float(row.conversion_factor or 1)
            break

    doc.custom_total_stock_uom = total / conversion_factor if conversion_factor else 0
