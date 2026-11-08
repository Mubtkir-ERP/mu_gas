frappe.ui.form.on("Gasco Statement Importer", {
	refresh(frm) {
		if (frm.doc.excel_file && !frm.is_new()) {
			frm.add_custom_button(__("مطابقة الكشف مع فواتير المشتريات 🔍"), () => {
				frappe.confirm(
					__("هل أنت متأكد من مطابقة كشف غازكو مع فواتير المشتريات المدخلة يدوياً بالنظام؟"),
					() => {
						frappe.call({
							method: "mu_gas.gasco_import.doctype.gasco_statement_importer.gasco_statement_importer.reconcile_statement_with_invoices",
							args: { importer_name: frm.doc.name },
							freeze: true,
							freeze_message: __("جاري مطابقة كشف غازكو وفحص الفواتير..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("اكتملت المطابقة بنجاح"),
										message: r.message.message,
										indicator: "green"
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}).addClass("btn-primary");
		}
	}
});
