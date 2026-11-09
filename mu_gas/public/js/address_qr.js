frappe.ui.form.on("Address", {
	refresh(frm) {
		frm.remove_custom_button("رمز QR لتسليم الفرع 🏷️", "الغاز");

		if (!frm.is_new()) {
			frm.add_custom_button(__("رمز QR لتسليم الفرع 🏷️"), () => {
				frappe.call({
					method: "mu_gas.gas_delivery.qr_utils.get_customer_delivery_qr",
					args: { address: frm.doc.name },
					freeze: true,
					freeze_message: __("جاري تجهيز رمز الـ QR للفرع..."),
					callback(r) {
						if (!r.message) return;
						let b = r.message;

						let d = new frappe.ui.Dialog({
							title: __("رمز QR لتسليم الفرع - {0}").replace("{0}", b.address_title),
							fields: [
								{
									fieldtype: "HTML",
									fieldname: "qr_card",
									options: `
										<div class="text-center p-3 border rounded bg-white shadow-sm" style="max-width: 350px; margin: 0 auto; direction: rtl;">
											<div style="font-size: 13px; font-weight: bold; color: #0284c7; margin-bottom: 2px;">🔥 تسليم الغاز للفرع</div>
											<div style="font-size: 17px; font-weight: 800; color: #0f172a;">${b.customer_name || b.customer || ''}</div>
											<div style="font-size: 14px; font-weight: 700; color: #10b981; margin-top: 2px;">🏢 ${b.address_title}</div>
											<div style="font-size: 11px; color: #64748b;">📍 ${b.address_line || ''} ${b.city || ''} | 📞 ${b.phone || ''}</div>
											
											<!-- Big clear QR Code on screen for scanning & testing -->
											<div id="print-area" style="display:flex; justify-content:center; align-items:center; margin: 14px 0; background: #fafafa; padding: 12px; border-radius: 12px; border: 1px solid #e2e8f0;">
												${b.qr_svg}
											</div>

											<!-- Direct Test Button -->
											<div class="mb-2">
												<a href="${b.delivery_url}" target="_blank" class="btn btn-primary btn-block font-weight-bold" style="display:block; padding: 9px; font-size: 13px; border-radius: 8px;">
													🚀 تجربة وفتح شاشة الطلب مباشرة 🔗
												</a>
											</div>

											<div style="font-size: 10px; color: #64748b; word-break: break-all; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #f1f5f9;">
												${b.delivery_url}
											</div>
											<div style="font-size: 10px; color: #94a3b8; margin-top: 6px;">يمكنك توجيه كاميرا الجوال على الشاشة الآن لمسح الرمز وتجربته فوراً</div>
										</div>
									`
								}
							],
							primary_action_label: __("طباعة الملصق 🖨️"),
							primary_action() {
								let printContents = `
									<div style="text-align: center; padding: 25px; font-family: sans-serif; direction: rtl;">
										<div style="border: 2px solid #0f172a; border-radius: 14px; padding: 18px; max-width: 320px; margin: 0 auto;">
											<h3 style="margin: 0; color: #0284c7;">🔥 تسليم الغاز للفرع</h3>
											<h2 style="margin: 6px 0; font-size: 20px;">${b.customer_name || b.customer || ''}</h2>
											<h3 style="margin: 4px 0; color: #10b981;">🏢 ${b.address_title}</h3>
											<p style="margin: 4px 0; font-size: 12px; color: #64748b;">📍 ${b.address_line || ''} ${b.city || ''} | 📞 ${b.phone || ''}</p>
											<div style="margin: 12px auto; max-width: 200px;">${b.qr_svg}</div>
											<div style="font-size: 10px; color: #64748b; word-break: break-all;">${b.delivery_url}</div>
										</div>
									</div>
								`;
								let w = window.open('', '_blank', 'width=450,height=600');
								w.document.write('<html><head><title>ملصق QR</title><style>body{margin:0;padding:10px;}</style></head><body>' + printContents + '</body></html>');
								w.document.close();
								w.focus();
								setTimeout(() => { w.print(); }, 400);
							}
						});
						d.show();
					}
				});
			}).addClass("btn-primary");
		}
	}
});
