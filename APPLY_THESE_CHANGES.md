# Changes to Apply to Production Server

## File 1: apps/c4pricing/c4pricing/api/item_code_rules.py

### Change 1: Update Asset Item naming (around line 71-76)
**Find:**
```python
    # Asset Item → ASS-YY-{Group}-###
    if t in ("asset item", "asset"):
        yy = now_datetime().strftime("%y")
        g = _group_abr(item_group)
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"ASS-{yy}-{g}-.###")
```

**Replace with:**
```python
    # Asset Item → ASS-{Group}-###
    if t in ("asset item", "asset"):
        g = _group_abr(item_group)
        if not g:
            frappe.throw("Please set <b>custom_abr</b> on the selected <b>Item Group</b>.")
        return make_autoname(f"ASS-{g}-.###")
```

### Change 2: Add Services naming rule (around line 79-80, after Accessories)
**Find:**
```python
    # Accessories → ACS-####
    if t == "accessories":
        return make_autoname("ACS-.####")

    # Part → PRT-(main_product)-(part_type) with uniqueness
```

**Replace with:**
```python
    # Accessories → ACS-####
    if t == "accessories":
        return make_autoname("ACS-.####")

    # Services → SRV-###
    if t == "services" or t == "service":
        return make_autoname("SRV-.###")

    # Part → PRT-(main_product)-(part_type) with uniqueness
```

### Change 3: Update docstring (around line 49-57)
**Find:**
```python
    """
    Naming rules:
      - Standard Product     : {Brand.custom_abr}-{ItemGroup.custom_abr}-###
      - Asset Item           : ASS-YY-{ItemGroup.custom_abr}-###
      - Accessories          : ACS-####
      - Material Item        : MTR-{ItemGroup.custom_abr}-###
```

**Replace with:**
```python
    """
    Naming rules:
      - Standard Product     : {Brand.custom_abr}-{ItemGroup.custom_abr}-###
      - Asset Item           : ASS-{ItemGroup.custom_abr}-###
      - Accessories          : ACS-####
      - Services             : SRV-###
      - Material Item        : MTR-{ItemGroup.custom_abr}-###
```

---

## File 2: apps/c4pricing/c4pricing/public/js/doctype/item_autocode.js

### Change: Add Asset and Services item group filters (around line 20-35)
**Find:**
```javascript
    } else if (t === "standard product" || t === "customized product") {
      // Only under "Products" (immediate children are fine here)
      query_opts = { filters: { parent_item_group: ["=", "Products"] } };

    } else if (t === "accessories") {
      // Only under "Accessorise"
      query_opts = { filters: { parent_item_group: ["=", "Accessorise"] } };

    } else if (t === "material item") {
```

**Replace with:**
```javascript
    } else if (t === "standard product" || t === "customized product") {
      // Only under "Products" (immediate children are fine here)
      query_opts = { filters: { parent_item_group: ["=", "Products"] } };

    } else if (t === "asset item" || t === "asset") {
      // Only under "Asset"
      query_opts = { filters: { parent_item_group: ["=", "Asset"] } };

    } else if (t === "accessories") {
      // Only under "Accessorise"
      query_opts = { filters: { parent_item_group: ["=", "Accessorise"] } };

    } else if (t === "services" || t === "service") {
      // Force "Services" item group
      if (frm.doc.item_group !== "Services") {
        frm.set_value("item_group", "Services");
      }
      query_opts = { filters: { name: ["=", "Services"] } };

    } else if (t === "material item") {
```

### Change: Add Services field check (around line 85-88)
**Find:**
```javascript
    if (t === "asset item" || t === "asset") {
      if (!frm.doc.item_group) return;
    }

    try {
```

**Replace with:**
```javascript
    if (t === "asset item" || t === "asset") {
      if (!frm.doc.item_group) return;
    }
    // Services requires no additional fields
    if (t === "services" || t === "service") {
      // Services doesn't need item_group since it auto-sets
    }

    try {
```

---

## After Making Changes

Run these commands on the production server:
```bash
bench --site your-site-name clear-cache
bench build
bench restart
```

Or if using systemctl:
```bash
sudo systemctl restart frappe-bench-frappe-web
sudo systemctl restart frappe-bench-frappe-workers
```

Then do a hard refresh in the browser (Ctrl+Shift+R or Ctrl+F5).
