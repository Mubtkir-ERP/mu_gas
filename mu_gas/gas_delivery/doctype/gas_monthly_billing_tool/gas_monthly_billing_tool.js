frappe.ui.form.on("Gas Monthly Billing Tool", {
	refresh(frm) {
		frm.add_custom_button(__("Generate Monthly Invoices 📑"), () => {
			if (!frm.doc.customer) {
				frappe.msgprint(__("Please select customer first"));
				return;
			}
			frappe.confirm(
				__("Are you sure you want to generate consolidated Sales Invoices for unbilled deliveries of customer {0}?").replace("{0}", frm.doc.customer),
				() => {
					frappe.call({
						method: "mu_gas.gas_delivery.doctype.gas_monthly_billing_tool.gas_monthly_billing_tool.generate_monthly_invoices",
						args: {
							customer: frm.doc.customer,
							from_date: frm.doc.from_date,
							to_date: frm.doc.to_date,
							billing_mode: frm.doc.billing_mode,
							company: frm.doc.company
						},
						freeze: true,
						freeze_message: __("Generating consolidated Sales Invoices..."),
						callback(r) {
							if (r.message && r.message.success) {
								frappe.msgprint({
									title: __("Billing Completed"),
									message: r.message.message,
									indicator: "green"
								});
							}
						}
					});
				}
			);
		}).addClass("btn-primary");
	}
});
