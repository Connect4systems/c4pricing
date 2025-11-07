// c4pricing/public/js/doctype/pick_list.js
frappe.ui.form.on('Pick List', {
  refresh(frm) {
    // لا نضيف أي زر مخصص – نستخدم الزر القياسي الموجود في النظام فقط

    // تعبئة مخزن المصدر من Item Group Defaults إن كان فارغًا
    const company = frm.doc.company;
    (frm.doc.locations || []).forEach(row => {
      if (!row.warehouse && row.item_code) {
        fetch_default_wh(row, company);
      }
    });
  }
});

function fetch_default_wh(row, company) {
  frappe.call({
    method: 'c4pricing.api.stock_entry.get_item_group_default_wh',
    args: { item_code: row.item_code, company },
    callback: (r) => {
      const wh = r.message;
      if (wh) frappe.model.set_value(row.doctype, row.name, 'warehouse', wh);
    }
  });
}
