frappe.ui.form.on("BOQ", {
  refresh(frm) {
    // Replace old single-action button with a chooser dialog
    frm.add_custom_button(__("Update Costs"), async () => {
      // ensure we have a real docname (avoid calling server on unsaved draft)
      if (!frm.doc.name) {
        await frm.save();
      }

      const dialog = new frappe.ui.Dialog({
        title: __("Update Costs From"),
        fields: [
          {
            label: __("Source"),
            fieldname: "source",
            fieldtype: "Select",
            options: [
              { label: __("Price List"), value: "price_list" },
              { label: __("Valuation Rate"), value: "valuation" },
              { label: __("Last Purchase Rate"), value: "last_purchase" },
            ],
            default: "price_list",
            reqd: 1,
          },
          {
            label: __("Price List"),
            fieldname: "price_list",
            fieldtype: "Link",
            options: "Price List",
            default: "Standard Buying",
            depends_on: "eval:doc.source=='price_list'",
          },
        ],
        primary_action_label: __("Update"),
        primary_action: async (values) => {
          const source = values.source || "price_list";
          const price_list = values.price_list || "Standard Buying";

          await frappe.call({
            method: "c4pricing.c4pricing.doctype.boq.boq.update_boq_costs",
            args: {
              name: frm.doc.name,
              source,
              price_list, // ignored by server when source != "price_list"
            },
            freeze: true,
            freeze_message:
              source === "price_list"
                ? __("Updating costs from Price List…")
                : source === "valuation"
                ? __("Updating costs from Valuation Rate…")
                : __("Updating costs from Last Purchase Rate…"),
            callback: (r) => {
              if (!r.message) return;

              const msg =
                source === "price_list"
                  ? __("Updated {0} rows<br>Source: Price List ({1})<br>New Total Cost: {2}", [
                      r.message.updated_rows,
                      r.message.price_list,
                      format_currency(
                        r.message.new_total_cost,
                        frm.doc.currency || frappe.defaults.get_default("currency")
                      ),
                    ])
                  : source === "valuation"
                  ? __("Updated {0} rows<br>Source: Valuation Rate<br>New Total Cost: {1}", [
                      r.message.updated_rows,
                      format_currency(
                        r.message.new_total_cost,
                        frm.doc.currency || frappe.defaults.get_default("currency")
                      ),
                    ])
                  : __("Updated {0} rows<br>Source: Last Purchase Rate<br>New Total Cost: {1}", [
                      r.message.updated_rows,
                      format_currency(
                        r.message.new_total_cost,
                        frm.doc.currency || frappe.defaults.get_default("currency")
                      ),
                    ]);

              frappe.msgprint(msg);
              frm.reload_doc();
            },
          });

          dialog.hide();
        },
      });

      dialog.show();
    });
  },
});
