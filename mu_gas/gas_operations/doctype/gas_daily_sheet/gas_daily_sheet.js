frappe.ui.form.on("Gas Daily Sheet", {
	refresh(frm) {
		if (frm.doc.status === "مسودة" && !frm.is_new()) {
			frm.add_custom_button(__("إرسال للمحاسب للاعتماد 📤"), () => {
				frm.set_value("status", "مرسل للمحاسب");
				frm.save();
			}).addClass("btn-secondary");
		}

		if (frm.doc.status === "مرسل للمحاسب") {
			frm.add_custom_button(__("اعتماد المسير وتوليد الفواتير والقيود ⚡"), () => {
				frappe.confirm(
					__("هل أنت متأكد من اعتماد هذا المسير وتوليد فواتير المبيعات وقيود المصروفات التلقائية؟"),
					() => {
						frappe.call({
							method: "mu_gas.gas_operations.doctype.gas_daily_sheet.gas_daily_sheet.approve_and_generate_entries",
							args: { sheet_name: frm.doc.name },
							freeze: true,
							freeze_message: __("جاري إنشاء الفواتير والقيود المحاسبية..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("تم الاعتماد بنجاح"),
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
