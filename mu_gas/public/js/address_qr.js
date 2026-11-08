frappe.ui.form.on("Address", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("رمز QR لتسليم الفرع 🏷️"), () => {
				frappe.call({
					method: "mu_gas.gas_delivery.qr_utils.get_customer_delivery_qr",
					args: { address: frm.doc.name },
					freeze: true,
					freeze_message: __("جاري توليد رمز الـ QR للفرع..."),
					callback(r) {
						if (!r.message) return;
						let b = r.message;

						let d = new frappe.ui.Dialog({
							title: __("رمز QR لتسليم الفرع - {0}").replace("{0}", b.address_title),
							fields: [
								{
									fieldtype: "HTML",
									fieldname: "qr_preview",
									options: `
										<div id="print-branch-area" class="text-center p-4 border rounded bg-white shadow-sm" style="max-width: 320px; margin: 0 auto;">
											<div style="font-size: 14px; font-weight: bold; color: #1e293b; margin-bottom: 4px;">🔥 تسليم الغاز للفرع</div>
											<div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 2px;">${b.customer_name || b.customer || ''}</div>
											<div style="font-size: 13px; font-weight: 700; color: #0284c7; margin-bottom: 4px;">🏢 ${b.address_title}</div>
											<div style="font-size: 11px; color: #64748b; margin-bottom: 12px;">📍 ${b.address_line} ${b.city} | 📞 ${b.phone || ''}</div>
											<div style="display:flex; justify-content:center; align-items:center; margin-bottom: 10px;">
												${b.qr_svg}
											</div>
											<div style="font-size: 11px; color: #0284c7; font-weight: bold; word-break: break-all;">${b.delivery_url}</div>
											<div style="font-size: 10px; color: #94a3b8; margin-top: 8px;">يتم مسح الكود ليفتح شاشة التسليم للفرع مباشرة</div>
										</div>
									`
								}
							],
							primary_action_label: __("طباعة ملصق الفرع 🖨️"),
							primary_action() {
								let printContents = document.getElementById("print-branch-area").innerHTML;
								let w = window.open('', '', 'width=450,height=600');
								w.document.write('<html><head><title>ملصق QR فرع الغاز</title><style>body{font-family:sans-serif;direction:rtl;text-align:center;padding:20px;} img,svg{max-width:200px;margin:10px auto;display:block;}</style></head><body>' + printContents + '</body></html>');
								w.document.close();
								w.focus();
								setTimeout(() => { w.print(); w.close(); }, 300);
							}
						});
						d.show();
					}
				});
			}, __("الغاز"));
		}
	}
});

