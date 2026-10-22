frappe.ui.form.on("Gasco Statement Importer", {
	refresh(frm) {
		if (frm.doc.excel_file && (frm.doc.status === "Draft" || frm.doc.status === "مسودة" || frm.doc.status === "Previewed") && !frm.is_new()) {
			frm.add_custom_button(__("Preview Excel 📊"), () => {
				frappe.call({
					method: "mu_gas.gasco_import.doctype.gasco_statement_importer.gasco_statement_importer.preview_excel_data",
					args: { importer_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Analyzing GASCO Excel file..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: __("Statement analyzed successfully"), indicator: "green" });
							frm.reload_doc();
						}
					}
				});
			}).addClass("btn-secondary");

			frm.add_custom_button(__("Generate Purchase Invoices & Payments ⚡"), () => {
				frappe.confirm(
					__("Are you sure you want to generate Purchase Invoices and Payments for extracted GASCO statement records?"),
					() => {
						frappe.call({
							method: "mu_gas.gasco_import.doctype.gasco_statement_importer.gasco_statement_importer.process_and_create_invoices",
							args: { importer_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Generating GASCO purchase invoices and payments..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("Generation completed successfully"),
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
