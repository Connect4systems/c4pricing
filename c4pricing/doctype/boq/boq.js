frappe.ui.form.on("BOQ", {
  refresh(frm) {
    frm.add_custom_button(__("Update Costs"), async () => {
      await frappe.call({
        method: "c4pricing.c4pricing.doctype.boq.boq.update_boq_costs",
        args: { name: frm.doc.name, price_list: "Standard Buying" },
        freeze: true,
        freeze_message: __("Updating costs from Standard Buying..."),
        callback: (r) => {
          if (r.message) {
            frappe.msgprint(
              __("Updated rows: {0}<br>Price List: {1}<br>New Total Cost: {2}", [
                r.message.updated_rows,
                r.message.price_list,
                format_currency(r.message.new_total_cost, frm.doc.currency || frappe.defaults.get_default("currency")),
              ])
            );
            frm.reload_doc();
          }
        },
      });
    });
  },
});
