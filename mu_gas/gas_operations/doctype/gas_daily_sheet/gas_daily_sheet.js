frappe.ui.form.on("Gas Daily Sheet", {
	refresh(frm) {
		if ((frm.doc.status === "Draft" || frm.doc.status === "مسودة") && !frm.is_new()) {
			frm.add_custom_button(__("Submit to Accountant 📤"), () => {
				frm.set_value("status", "Submitted to Accountant");
				frm.save();
			}).addClass("btn-secondary");
		}

		if (frm.doc.status === "Submitted to Accountant" || frm.doc.status === "مرسل للمحاسب") {
			frm.add_custom_button(__("Approve Sheet & Generate Entries ⚡"), () => {
				frappe.confirm(
					__("Are you sure you want to approve this sheet and generate Sales Invoices and Journal Entries?"),
					() => {
						frappe.call({
							method: "mu_gas.gas_operations.doctype.gas_daily_sheet.gas_daily_sheet.approve_and_generate_entries",
							args: { sheet_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Generating invoices and journal entries..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("Approval Completed"),
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
