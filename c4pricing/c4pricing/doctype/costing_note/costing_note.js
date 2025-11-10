// c4pricing / Costing Note — HOTFIX, minimal and safe

// number helper
function F(v) {
  var n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

// compute suggested selling price
function compute_tsp(cost, marginPct) {
  return F(cost) * (1 + F(marginPct) / 100.0);
}

frappe.ui.form.on("Costing Note", {
  onload: function (frm) {
    // remember previously applied parent margin (for non-invasive updates)
    frm._prev_default_profit_margin = F(frm.doc.default_profit_margin);
  },

  refresh: function (frm) {
    // ensure the BOQ filter is wired for the grid link field
    try {
      if (
        frm.fields_dict &&
        frm.fields_dict["costing_note_items"] &&
        frm.fields_dict["costing_note_items"].grid &&
        frm.fields_dict["costing_note_items"].grid.get_field
      ) {
        frm.fields_dict["costing_note_items"].grid
          .get_field("boq_link")
          .get_query = function (doc, cdt, cdn) {
          var row = frappe.get_doc(cdt, cdn) || {};
          return {
            filters: {
              item: row.item || null, // filter BOQs by the row's Item
            },
          };
        };
      }
    } catch (e) {
      // never crash the form
      console.warn("Failed to set boq_link filter:", e);
    }

    // one-time gentle backfill: if a row TSP is blank, fill it from current parent margin
    try {
      (frm.doc.costing_note_items || []).forEach(function (r) {
        if (r.target_selling_price === undefined || r.target_selling_price === null || r.target_selling_price === "") {
          r.target_selling_price = compute_tsp(r.cost, frm.doc.default_profit_margin || 0);
        }
      });
      frm.refresh_field("costing_note_items");
    } catch (e) {
      console.warn("Backfill TSP failed:", e);
    }
  },

  // when the parent default margin changes, update rows that weren't customized
  default_profit_margin: function (frm) {
    var prev = F(frm._prev_default_profit_margin);
    var cur = F(frm.doc.default_profit_margin || 0);

    try {
      (frm.doc.costing_note_items || []).forEach(function (r) {
        var cost = F(r.cost);
        var prev_formula = compute_tsp(cost, prev);
        var cur_formula = compute_tsp(cost, cur);

        var cur_tsp = r.target_selling_price;
        var is_blank = cur_tsp === undefined || cur_tsp === null || cur_tsp === "";
        var matches_prev = F(cur_tsp) === F(prev_formula);

        if (is_blank || matches_prev) {
          r.target_selling_price = cur_formula; // adopt new base margin
        }
      });
      frm.refresh_field("costing_note_items");
    } catch (e) {
      console.warn("default_profit_margin propagation failed:", e);
    }

    frm._prev_default_profit_margin = cur;
  },
});

frappe.ui.form.on("Costing Note Items", {
  // If user fills/changes cost, set TSP only when currently blank
  cost: function (frm, cdt, cdn) {
    try {
      var row = frappe.get_doc(cdt, cdn);
      if (row && (row.target_selling_price === undefined || row.target_selling_price === null || row.target_selling_price === "")) {
        row.target_selling_price = compute_tsp(row.cost, frm.doc.default_profit_margin || 0);
        frm.refresh_field("costing_note_items");
      }
    } catch (e) {
      console.warn("cost handler failed:", e);
    }
  },

  // reapply filter if item changes
  item: function (frm, cdt, cdn) {
    try {
      if (
        frm.fields_dict &&
        frm.fields_dict["costing_note_items"] &&
        frm.fields_dict["costing_note_items"].grid &&
        frm.fields_dict["costing_note_items"].grid.get_field
      ) {
        frm.fields_dict["costing_note_items"].grid
          .get_field("boq_link")
          .get_query = function (doc, _cdt, _cdn) {
          var row = frappe.get_doc(cdt, cdn) || {};
          return {
            filters: {
              item: row.item || null,
            },
          };
        };
      }
    } catch (e) {
      console.warn("re-apply boq_link filter failed:", e);
    }
  },

  // Link (or re-link) a BOQ → pull the total into cost, keep your current flow intact
  boq_link: async function (frm, cdt, cdn) {
    var row = frappe.get_doc(cdt, cdn);
    if (!row || !row.boq_link) return;

    try {
      await frappe.call({
        method: "c4pricing.api.get_boq_totals",
        args: { boq_name: row.boq_link },
        callback: function (r) {
          if (!r || !r.message) return;
          var tc = F(r.message.total_cost);
          frappe.model.set_value(cdt, cdn, "cost", tc);
          frappe.model.set_value(cdt, cdn, "total_cost", tc * F(row.qty));
          // if TSP is blank, fill from parent margin now
          if (row.target_selling_price === undefined || row.target_selling_price === null || row.target_selling_price === "") {
            frappe.model.set_value(cdt, cdn, "target_selling_price", compute_tsp(tc, frm.doc.default_profit_margin || 0));
          }
        },
      });
    } catch (e) {
      console.warn("boq_link handler failed:", e);
    }
  },

  // Keep your existing BOQ create/link button workflow working as before (if you had one)
  boq: async function (frm, cdt, cdn) {
    try {
      if (!frm.doc.name || frm.is_dirty()) {
        await frm.save();
      }
      var row = frappe.get_doc(cdt, cdn);
      await frappe.call({
        method: "c4pricing.api.create_boq",
        args: { source_name: frm.doc.name, item_row: row },
        freeze: true,
        freeze_message: __("Creating BOQ..."),
        callback: function (r) {
          if (r && r.message && r.message.name) {
            frappe.model.set_value(cdt, cdn, "boq_link", r.message.name);
            frappe.set_route("Form", "BOQ", r.message.name);
          }
        },
      });
    } catch (e) {
      console.warn("boq button failed:", e);
    }
  },
});
