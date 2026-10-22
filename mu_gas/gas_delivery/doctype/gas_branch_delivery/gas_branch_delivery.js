frappe.ui.form.on("Gas Branch Delivery", {
	refresh(frm) {
		if (frm.doc.status === "Pending OTP" && !frm.is_new()) {
			frm.add_custom_button(__("إرسال كود التحقق للفرع 📲"), () => {
				frappe.call({
					method: "mu_gas.gas_delivery.doctype.gas_branch_delivery.gas_branch_delivery.send_delivery_otp",
					args: { delivery_name: frm.doc.name },
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: r.message.message, indicator: "green" });
						}
					}
				});
			}).addClass("btn-primary");

			frm.add_custom_button(__("إدخال كود التحقق وتأكيد التسليم ✔️"), () => {
				frappe.prompt(
					[
						{
							fieldname: "otp_code",
							fieldtype: "Data",
							label: __("كود التحقق المستلم من الفرع"),
							reqd: 1
						}
					],
					(values) => {
						frappe.call({
							method: "mu_gas.gas_delivery.doctype.gas_branch_delivery.gas_branch_delivery.verify_otp_and_confirm",
							args: {
								delivery_name: frm.doc.name,
								input_otp: values.otp_code
							},
							callback(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({ message: r.message.message, indicator: "green" });
									frm.reload_doc();
								}
							}
						});
					},
					__("التحقق من استلام الفرع"),
					__("تأكيد التسليم وإنشاء سند الإخراج")
				);
			}).addClass("btn-success");
		}
	}
});
