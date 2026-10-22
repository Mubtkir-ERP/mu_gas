frappe.ui.form.on("Gas Branch Delivery", {
	refresh(frm) {
		if (frm.doc.status === "Pending OTP" && !frm.is_new()) {
			frm.add_custom_button(__("Send Branch OTP 📲"), () => {
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

			frm.add_custom_button(__("Verify OTP & Confirm Delivery ✔️"), () => {
				frappe.prompt(
					[
						{
							fieldname: "otp_code",
							fieldtype: "Data",
							label: __("Branch OTP Code"),
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
					__("Verify Branch Receipt"),
					__("Confirm Delivery & Create Delivery Note")
				);
			}).addClass("btn-success");
		}
	}
});
