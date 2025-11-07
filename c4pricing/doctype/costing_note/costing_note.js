// Costing Note client script (c4pricing)
frappe.ui.form.on("Costing Note Items", {
  // Row button "BOQ"
  boq(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    frappe.call({
      method: "c4pricing.api.create_boq",          // ✅ correct path
      args: {
        source_name: frm.doc.name,
        item_row: row,
      },
      freeze: true,
      freeze_message: __("Creating BOQ..."),
      callback: (r) => {
        if (r.message && r.message.name) {
          // store link then open the BOQ
          frappe.model.set_value(cdt, cdn, "boq_link", r.message.name);
          frappe.set_route("Form", "BOQ", r.message.name);
        }
      },
    });
  },

  // When user selects/changes an existing BOQ
  boq_link(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (!row.boq_link) return;

    frappe.call({
      method: "c4pricing.api.get_boq_totals",      // ✅ correct path
      args: { boq_name: row.boq_link },
      callback: (r) => {
        if (!r.message) return;
        const tc = r.message.total_cost || 0;
        frappe.model.set_value(cdt, cdn, "cost", tc);
        frappe.model.set_value(cdt, cdn, "total_cost", tc * (row.qty || 0));
        frm.save();
      },
    });
  },
});
