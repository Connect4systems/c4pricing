// c4pricing/public/js/doctype/opportunity.js 
(() => {
  // --- SET THIS if your Standard Product child doctype name differs ---
  const STANDARD_CHILD_DT = "Opportunity Standard (C4)"; // <-- change to your child DocType name

  // ------------- pricing helpers -------------
  async function get_last_selling_rate(item_code, price_list) {
    const rows = await frappe.db.get_list("Item Price", {
      fields: ["price_list_rate"],
      filters: { item_code, selling: 1, ...(price_list ? { price_list } : {}) },
      order_by: "modified desc",
      limit: 1,
    });
    return (rows && rows.length && flt(rows[0].price_list_rate)) || 0;
  }

  function recalc_row(row) {
    row.rate = flt(row.rate) || 0;
    row.qty = flt(row.qty) || 0;
    row.amount = row.rate * row.qty;
    row.base_rate = row.rate;
    row.base_amount = row.amount;
  }

  function insert_to_custom_standard(frm, it) {
    frm.add_child("custom_standard", {
      item: it.name,
      item_name: it.item_name,
      description: it.description,
      uom: it.stock_uom,
      qty: 1,
      rate: 0,
      amount: 0,
    });
    frm.refresh_field("custom_standard");
  }

  function insert_to_items(frm, it) {
    frm.add_child("items", {
      item_code: it.name,
      item_name: it.item_name,
      description: it.description,
      uom: it.stock_uom,
      qty: 1,
      rate: 0,
      amount: 0,
      base_rate: 0,
      base_amount: 0,
    });
    frm.refresh_field("items");
  }

  async function handle_new_row_price(frm, grid_fieldname, rowname, item_fieldname) {
    const v = frm.doc || {};
    const row = frappe.get_doc(frm.fields_dict[grid_fieldname].grid.doctype, rowname);
    const code = row[item_fieldname];
    if (!code) return;

    const pl = (v.selling_price_list || v.price_list || null);
    const rate = await get_last_selling_rate(code, pl);
    row.rate = rate || 0;
    recalc_row(row);
    frm.refresh_field(grid_fieldname);
  }

  // ------------- selector helpers -------------
  const esc = frappe.utils.escape_html;

  function img(src) {
    if (!src) return "";
    return `<div class="p-2"><img style="max-width:100%;max-height:280px;border-radius:8px" src="${frappe.urllib.get_full_url(src)}"/></div>`;
  }

  function strip_html(html) {
    try {
      const tmp = document.createElement("div");
      tmp.innerHTML = html || "";
      return (tmp.textContent || tmp.innerText || "").trim();
    } catch (e) {
      return (html || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }
  }

  // Row for results table (with Add button)
  function resultRow(it) {
    return `
      <tr class="c4p-row" data-code="${esc(it.name)}" style="cursor:pointer">
        <td>${esc(it.name)}</td>
        <td>${esc(it.item_name || "")}</td>
        <td>${esc(it.custom_material_line || "")}</td>
        <td>${esc(it.item_group || "")}</td>
        <td style="width:80px">
          <button class="btn btn-xs btn-primary c4p-add" data-code="${esc(it.name)}">${__("Add")}</button>
        </td>
      </tr>`;
  }

  // ---- fetch items with DIMENSIONS filtering ----
  async function fetchItems({ item_type, brand, item_group, material_line, txt, limit, w, h, d }) {
    const filters = { disabled: 0 };
    if (item_type)     filters["custom_item_type"]     = item_type;   // "Standard Product" | "Customized Product"
    if (brand)         filters["brand"]                = brand;
    if (item_group)    filters["item_group"]           = item_group;
    if (material_line) filters["custom_material_line"] = material_line;

    // exact match numeric filtering if values are provided
    const wv = (w !== undefined && w !== null && String(w).trim() !== "") ? flt(w) : null;
    const hv = (h !== undefined && h !== null && String(h).trim() !== "") ? flt(h) : null;
    const dv = (d !== undefined && d !== null && String(d).trim() !== "") ? flt(d) : null;

    if (wv !== null) filters["custom_width"]  = ["=", wv];
    if (hv !== null) filters["custom_hight"]  = ["=", hv];   // spelling per your schema
    if (dv !== null) filters["custom_depth"]  = ["=", dv];

    return await frappe.db.get_list("Item", {
      fields: [
        "name","item_name","description","stock_uom","image",
        "item_group","custom_material_line",
        "custom_width","custom_hight","custom_depth"
      ],
      filters,
      or_filters: txt ? [
        ["Item","name","like",`%${txt}%`],
        ["Item","item_name","like",`%${txt}%`],
        ["Item","description","like",`%${txt}%`],
      ] : [],
      order_by: "item_name asc",
      limit: cint(limit || 20),
    });
  }

  function openItemSelector(frm) {
    const d = new frappe.ui.Dialog({
      title: __("Select Item"),
      size: "extra-large",
      fields: [
        // ====== Section 1 (3 columns) ======
        { fieldtype: "Section Break", label: __("Filters") },

        // Column 1
        { fieldtype: "Column Break" },
        { label: __("Item Type"), fieldname: "custom_item_type", fieldtype: "Select",
          options: ["Standard Product","Customized Product"], default: "Standard Product", reqd: 1 },
        { label: __("Material Line"), fieldname: "custom_material_line", fieldtype: "Link", options: "Material Line" },
        { label: __("Search text"), fieldname: "q", fieldtype: "Data", placeholder: __("Type to search…") },

        // Column 2
        { fieldtype: "Column Break" },
        { label: __("Item Group"), fieldname: "item_group", fieldtype: "Link", options: "Item Group",
          get_query: () => ({ filters: { custom_allow_sales: 1 } }) },
        { label: __("Brand"), fieldname: "brand", fieldtype: "Link", options: "Brand",
          depends_on: "eval:doc.custom_item_type=='Standard Product'" },
        { label: __("Results per page"), fieldname: "limit", fieldtype: "Select", options: "10\n20", default: "20" },

        // Column 3 (Dimensions stacked)
        { fieldtype: "Column Break" },
        { label: __("Width (W)"),  fieldname: "custom_width",  fieldtype: "Float" },
        { label: __("Height (H)"), fieldname: "custom_height", fieldtype: "Float" },
        { label: __("Depth (D)"),  fieldname: "custom_depth",  fieldtype: "Float" },

        // Apply
        { fieldtype: "Section Break" },
        { fieldtype: "Button", label: __("Apply Filters"), fieldname: "apply" },

        // ====== Section 2 (Results + Preview) ======
        { fieldtype: "Section Break", label: __("Selector") },

        // Left column = results table
        { fieldtype: "Column Break" },
        { fieldtype: "HTML", fieldname: "results_html" },

        // Right column = preview card
        { fieldtype: "Column Break" },
        { fieldtype: "HTML", fieldname: "preview_html" },
      ],
      primary_action_label: __("Close"),
      primary_action: () => d.hide(),
    });

    const $res = d.get_field("results_html").$wrapper;
    const $prev = d.get_field("preview_html").$wrapper;

    // Results table with 5 columns
    $res.html(`
      <div style="max-height:520px;overflow:auto;border:1px solid var(--border-color);border-radius:8px">
        <table class="table table-bordered table-hover" style="margin:0">
          <thead>
            <tr>
              <th>${__("Item Code")}</th>
              <th>${__("Item Name")}</th>
              <th>${__("Material Line")}</th>
              <th>${__("Item Group")}</th>
              <th style="width:80px">${__("Add")}</th>
            </tr>
          </thead>
          <tbody class="c4p-body"></tbody>
        </table>
      </div>
      <div class="text-muted mt-2">${__("Click Add to insert the item")}</div>
    `);

    // Preview card
    $prev.html(`
      <div style="border:1px solid var(--border-color);border-radius:8px;min-height:520px;padding:10px">
        <div class="c4p-preview-muted text-muted">${__("Hover or select an item to preview…")}</div>
        <div class="c4p-preview"></div>
      </div>
    `);

    const $body = $res.find(".c4p-body");
    const $preview = $prev.find(".c4p-preview");
    const $muted = $prev.find(".c4p-preview-muted");

    const refreshList = async () => {
      const v = d.get_values();
      const items = await fetchItems({
        item_type: v.custom_item_type,
        brand: v.brand,
        item_group: v.item_group,
        material_line: v.custom_material_line,
        txt: v.q,
        limit: v.limit,
        w: v.custom_width,
        h: v.custom_height,
        d: v.custom_depth,
      });

      $body.empty();
      if (!items.length) {
        $body.append(`<tr><td colspan="5" class="text-muted text-center">${__("No items found")}</td></tr>`);
        $muted.show(); $preview.html("");
        return;
      }

      items.forEach((it) => $body.append(resultRow(it)));

      // Hover shows preview
      $body.find(".c4p-row").on("mouseenter", function () {
        const code = this.dataset.code;
        const it = items.find((x) => x.name === code);
        if (!it) return;
        const dims = [it.custom_width, it.custom_hight, it.custom_depth]
          .map(v => (v==null || v==="") ? "-" : String(v)).join(" × ");

        $muted.hide();
        $preview.html(`
          <div class="p-2">
            <div class="mb-1" style="font-weight:600">${esc(it.item_name || it.name)}</div>
            <div class="text-muted mb-1">${esc(it.name)}</div>
            ${img(it.image)}
            <div class="mb-2" style="white-space:pre-wrap">${esc(strip_html(it.description) || "")}</div>
            <div class="grid" style="grid-template-columns: repeat(2, minmax(0,1fr)); gap:8px">
              <div><span class="text-muted">${__("Material Line")}:</span> ${esc(it.custom_material_line || "-")}</div>
              <div><span class="text-muted">${__("Item Group")}:</span> ${esc(it.item_group || "-")}</div>
            </div>
            <div class="mt-2"><span class="text-muted">${__("Dimensions")}:</span> ${esc(dims)}</div>
            <div class="text-muted">${__("UOM")}: ${esc(it.stock_uom || "-")}</div>
          </div>
        `);
      });

      // Add button + click on row
      async function addItemByCode(code) {
        const it = items.find((x) => x.name === code);
        if (!it) return;
        const isStd = (d.get_value("custom_item_type") === "Standard Product");
        if (isStd) insert_to_custom_standard(frm, it);
        else insert_to_items(frm, it);

        const grid_field = isStd ? "custom_standard" : "items";
        const last_row = frm.doc[grid_field][frm.doc[grid_field].length - 1];
        await handle_new_row_price(
          frm, grid_field, last_row.name, isStd ? "item" : "item_code"
        );
        frappe.show_alert({ message: __("Item added: ") + it.name, indicator: "green" });
      }

      $body.find(".c4p-add").on("click", async function (e) {
        e.preventDefault(); e.stopPropagation();
        await addItemByCode(this.dataset.code);
      });
      $body.find(".c4p-row").on("click", async function () {
        await addItemByCode(this.dataset.code);
      });
    };

    // Auto refresh on filters + Apply button
    ["custom_item_type","brand","item_group","custom_material_line","q","limit","custom_width","custom_height","custom_depth"]
      .forEach(fn => { const f = d.fields_dict[fn]; if (f?.$input) f.$input.on("change", refreshList); });

    d.get_field("apply").$input.on("click", refreshList);

    d.show();
    refreshList();
  }

  // ------------- doctype wiring -------------
  frappe.ui.form.on("Opportunity", {
    refresh(frm) {
      // Create Costing Note (as you configured)
      if (!frm.is_new()) {
        frm.add_custom_button(__("Costing Note"), () => {
          frappe.model.open_mapped_doc({
            method: "c4pricing.api.create_costing_note",
            frm: frm,
            args: { doctype: "Opportunity" },
          });
        }, __("Create"));
      }

      // Selector button
      frm.add_custom_button(__("Select Item"), () => openItemSelector(frm), __("Add"));
    },
  });

  // standard items table: math + last price
  frappe.ui.form.on("Opportunity Item", {
    items_add(frm, cdt, cdn) {
      const r = locals[cdt][cdn];
      r.rate = 0; r.amount = 0; r.base_rate = 0; r.base_amount = 0;
      frm.refresh_field("items");
    },
    item_code: async function (frm, cdt, cdn) {
      const r = locals[cdt][cdn];
      await handle_new_row_price(frm, "items", r.name, "item_code");
    },
    rate: function (frm, cdt, cdn) { recalc_row(locals[cdt][cdn]); frm.refresh_field("items"); },
    qty: function (frm, cdt, cdn)  { recalc_row(locals[cdt][cdn]); frm.refresh_field("items"); },
  });

  // standard products table (your custom child)
  frappe.ui.form.on(STANDARD_CHILD_DT, {
    item: async function (frm, cdt, cdn) {
      const r = locals[cdt][cdn];
      await handle_new_row_price(frm, "custom_standard", r.name, "item");
    },
    rate: function (frm, cdt, cdn) { recalc_row(locals[cdt][cdn]); frm.refresh_field("custom_standard"); },
    qty: function (frm, cdt, cdn)  { recalc_row(locals[cdt][cdn]); frm.refresh_field("custom_standard"); },
  });
})();
