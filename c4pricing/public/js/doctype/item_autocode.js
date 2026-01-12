// c4pricing/public/js/doctype/item_autocode.js
(function () {
  function get_item_type(frm) {
    return frm.doc.custom_item_type || frm.doc.item_type || null;
  }

  async function apply_item_group_filter(frm) {
    const t = (get_item_type(frm) || "").trim().toLowerCase();
    
    // Debug logging
    console.log("=== ITEM GROUP FILTER DEBUG ===");
    console.log("Item Type:", get_item_type(frm));
    console.log("Normalized:", t);

    // Default: clear custom query
    let query_opts = { filters: {} };

    if (t === "part" || t === "wip") {
      // Force "Sub Assemblies" only
      if (frm.doc.item_group !== "Sub Assemblies") {
        frm.set_value("item_group", "Sub Assemblies");
      }
      query_opts = { filters: { name: ["=", "Sub Assemblies"] } };

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
      // All descendants of "Materials": use lft/rgt bounds from server
      try {
        const r = await frappe.call({
          method: "c4pricing.api.bounds",
          args: { parent_group: "Materials" },
        });
        if (r && r.message) {
          const { lft, rgt } = r.message;
          // Only leaf groups (is_group = 0) within the subtree
          query_opts = { filters: { lft: [">=", lft], rgt: ["<=", rgt], is_group: 0 } };
        }
      } catch (e) {
        console.error("Materials bounds error:", e);
        // Fallback (at least limit to direct children)
        query_opts = { filters: { parent_item_group: ["=", "Materials"] } };
      }
    }

    frm.set_query("item_group", () => query_opts);
  }

  async function fill_code(frm) {
    const item_type = get_item_type(frm);
    if (!item_type) return;
    if (frm.doc.item_code) return;

    const t = String(item_type || "").trim().toLowerCase();

    // Wait for required fields by rule
    if (t === "standard product") {
      if (!frm.doc.brand || !frm.doc.item_group) return;
    }
    if (t === "material item") {
      if (!frm.doc.item_group) return;
    }
    if (t === "customized product") {
      if (!frm.doc.item_group) return;
    }
    if (t === "part") {
      if (!frm.doc.custom_main_product || !frm.doc.custom_part_type) return;
    }
    if (t === "wip") {
      if (!frm.doc.custom_main_product || !frm.doc.item_name) return;
    }
    if (t === "asset item" || t === "asset") {
      if (!frm.doc.item_group) return;
    }
    // Services requires no additional fields
    if (t === "services" || t === "service") {
      // Services doesn't need item_group since it auto-sets
    }

    try {
      const r = await frappe.call({
        method: "c4pricing.api.next_code",
        args: {
          item_type: item_type,
          item_group: frm.doc.item_group || null,
          brand: frm.doc.brand || null,
          main_product: frm.doc.custom_main_product || null,
          part_type: frm.doc.custom_part_type || null,
          item_name: frm.doc.item_name || null,
        },
      });
      if (r && r.message) {
        frm.set_value("item_code", r.message);
      }
    } catch (e) {
      console.error(e);
      frappe.msgprint({
        title: __("Auto Code Error"),
        message: e.message || e,
        indicator: "red",
      });
    }
  }

  frappe.ui.form.on("Item", {
    onload_post_render: apply_item_group_filter,
    refresh: apply_item_group_filter,
    custom_item_type(frm) { apply_item_group_filter(frm); fill_code(frm); },
    item_type(frm) { apply_item_group_filter(frm); fill_code(frm); },
    item_group: fill_code,
    brand: fill_code,
    custom_main_product: fill_code,
    custom_part_type: fill_code,
    item_name: fill_code,
    validate: fill_code,
  });
})();
