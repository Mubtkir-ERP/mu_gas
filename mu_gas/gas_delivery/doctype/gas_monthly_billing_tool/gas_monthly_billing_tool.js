frappe.ui.form.on("Gas Monthly Billing Tool", {
	refresh(frm) {
		frm.add_custom_button(__("توليد فواتير المبيعات المجمعة 📑"), () => {
			if (!frm.doc.customer) {
				frappe.msgprint(__("يرجى اختيار العميل أولاً"));
				return;
			}
			frappe.confirm(
				__("هل أنت متأكد من توليد فواتير المبيعات المجمعة لسندات التسليم غير المفوترة للعميل {0}؟").format(frm.doc.customer),
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
						freeze_message: __("جاري إنشاء فواتير المبيعات المجمعة..."),
						callback(r) {
							if (r.message && r.message.success) {
								frappe.msgprint({
									title: __("تمت الفوترة بنجاح"),
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
