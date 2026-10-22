frappe.ui.form.on("Gasco Statement Importer", {
	refresh(frm) {
		if (frm.doc.excel_file && frm.doc.status === "مسودة" && !frm.is_new()) {
			frm.add_custom_button(__("معاينة وتحليل الإكسل 📊"), () => {
				frappe.call({
					method: "mu_gas.gasco_import.doctype.gasco_statement_importer.gasco_statement_importer.preview_excel_data",
					args: { importer_name: frm.doc.name },
					freeze: true,
					freeze_message: __("جاري تحليل ملف إكسل غازكو..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: __("تم تحليل الكشف بنجاح"), indicator: "green" });
							frm.reload_doc();
						}
					}
				});
			}).addClass("btn-secondary");

			frm.add_custom_button(__("توليد فواتير المشتريات والسداد التلقائي ⚡"), () => {
				frappe.confirm(
					__("هل أنت متأكد من توليد فواتير المشتريات وسندات السداد التلقائية لجميع مسحوبات غازكو المستخرجة؟"),
					() => {
						frappe.call({
							method: "mu_gas.gasco_import.doctype.gasco_statement_importer.gasco_statement_importer.process_and_create_invoices",
							args: { importer_name: frm.doc.name },
							freeze: true,
							freeze_message: __("جاري إنشاء فواتير مشتريات غازكو وسندات الصرف..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("اكتمل التوليد بنجاح"),
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
