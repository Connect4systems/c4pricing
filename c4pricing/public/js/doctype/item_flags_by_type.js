// c4pricing/public/js/doctype/item_flags_by_type.js
(function () {
  function normalize(v) {
    return String(v || "").trim().toLowerCase();
  }

  function flagsFor(typeName) {
    const t = normalize(typeName);
    // Defaults: do nothing if unknown
    const NONE = null;

    if (["standard product", "customized product"].includes(t)) {
      return { is_purchase_item: 0, is_sales_item: 1, is_stock_item: 1, is_fixed_asset: 0 };
    }
    if (["material item", "accessories"].includes(t)) {
      return { is_purchase_item: 1, is_sales_item: 0, is_stock_item: 1, is_fixed_asset: 0 };
    }
    if (t === "asset") {
      return { is_purchase_item: 1, is_sales_item: 0, is_stock_item: 0, is_fixed_asset: 1 };
    }
    if (t === "service item") {
      return { is_purchase_item: 1, is_sales_item: 1, is_stock_item: 0, is_fixed_asset: 0 };
    }
    // Unknown type → don’t change anything
    return NONE;
  }

  async function applyFlags(frm) {
    const typeName = frm.doc.custom_item_type;
    if (!typeName) return;
    const f = flagsFor(typeName);
    if (!f) return;

    // Set values only if different to avoid needless dirtying/re-renders
    Object.entries(f).forEach(([k, v]) => {
      if (frm.doc[k] !== v) {
        frm.set_value(k, v);
      }
    });
  }

  frappe.ui.form.on("Item", {
    onload_post_render: applyFlags,
    refresh: applyFlags,
    custom_item_type: applyFlags,
  });
})();
