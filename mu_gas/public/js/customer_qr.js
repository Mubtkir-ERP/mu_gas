frappe.ui.form.on("Customer", {
	refresh(frm) {
		// Remove old buttons from previous scripts or customizations
		frm.remove_custom_button("طباعة QR الفروع");
		frm.remove_custom_button("طباعة QR الفروع", "الغاز");
		frm.remove_custom_button("رمز QR لتسليم الغاز 🏷️", "الغاز");
		setTimeout(() => {
			frm.page.wrapper.find('button:contains("طباعة QR الفروع")').remove();
		}, 100);

		if (!frm.is_new()) {
			// Show new button directly on top bar (no dropdown menu)
			frm.add_custom_button(__("رمز QR لتسليم الغاز 🏷️"), () => {
				frappe.call({
					method: "mu_gas.gas_delivery.qr_utils.get_customer_delivery_qr",
					args: { customer: frm.doc.name },
					freeze: true,
					freeze_message: __("جاري تجهيز رمز الـ QR..."),
					callback(r) {
						if (!r.message) return;
						let data = r.message;

						if (!data.has_branches) {
							// Single Customer without branches
							show_gas_qr_modal(data, __("رمز QR لتسليم الغاز - {0}").replace("{0}", data.customer_name));
						} else {
							// Customer has multiple branches: list them with preview & direct test links
							let rowsHtml = data.branches.map((b, idx) => `
								<div class="p-3 mb-2 border rounded bg-white shadow-sm" style="direction: rtl;">
									<div class="d-flex justify-content-between align-items-center mb-2">
										<div>
											<div class="font-weight-bold text-dark" style="font-size: 14px;">🏢 ${b.address_title}</div>
											<small class="text-muted">📍 ${b.address_line || ''} ${b.city || ''} ${b.phone ? '| 📞 ' + b.phone : ''}</small>
										</div>
									</div>
									<div class="d-flex gap-2" style="gap: 8px;">
										<button type="button" class="btn btn-sm btn-primary preview-branch-btn" data-idx="${idx}">
											👁️ عرض وتجربة الـ QR
										</button>
										<a href="${b.delivery_url}" target="_blank" class="btn btn-sm btn-outline-info">
											🚀 فتح شاشة الطلب مباشرة 🔗
										</a>
									</div>
								</div>
							`).join("");

							let d = new frappe.ui.Dialog({
								title: __("رموز QR لفروع العميل: {0}").replace("{0}", data.customer_name),
								fields: [
									{
										fieldtype: "HTML",
										fieldname: "branches_list",
										options: `
											<div style="max-height: 420px; overflow-y: auto; direction: rtl;">
												<p class="text-muted small mb-3">اختر الفرع لعرض الـ QR أو لفتح شاشة الطلب مباشرة وتجربتها:</p>
												${rowsHtml}
											</div>
										`
									}
								]
							});
							d.show();

							d.$wrapper.find('.preview-branch-btn').on('click', function() {
								let idx = $(this).data('idx');
								let b = data.branches[idx];
								show_gas_qr_modal({
									customer: data.customer,
									customer_name: data.customer_name,
									address_title: b.address_title,
									address_line: b.address_line,
									city: b.city,
									delivery_url: b.delivery_url,
									qr_svg: b.qr_svg
								}, __("رمز QR لفرع: {0}").replace("{0}", b.address_title));
							});
						}
					}
				});
			}).addClass("btn-primary");
		}
	}
});

function show_gas_qr_modal(data, title) {
	let d = new frappe.ui.Dialog({
		title: title || __("رمز QR لتسليم الغاز"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "qr_card",
				options: `
					<div class="text-center p-3 border rounded bg-white shadow-sm" style="max-width: 350px; margin: 0 auto; direction: rtl;">
						<div style="font-size: 13px; font-weight: bold; color: #0284c7; margin-bottom: 2px;">🔥 تسليم الغاز</div>
						<div style="font-size: 17px; font-weight: 800; color: #0f172a;">${data.customer_name || ''}</div>
						${data.address_title ? `<div style="font-size: 14px; font-weight: 700; color: #10b981; margin-top: 2px;">🏢 ${data.address_title}</div>` : ''}
						${data.address_line ? `<div style="font-size: 11px; color: #64748b;">📍 ${data.address_line} ${data.city || ''}</div>` : ''}
						
						<!-- Big clear QR Code on screen for scanning & testing -->
						<div id="print-area" style="display:flex; justify-content:center; align-items:center; margin: 14px 0; background: #fafafa; padding: 12px; border-radius: 12px; border: 1px solid #e2e8f0;">
							${data.qr_svg}
						</div>

						<!-- Direct Test Button -->
						<div class="mb-2">
							<a href="${data.delivery_url}" target="_blank" class="btn btn-primary btn-block font-weight-bold" style="display:block; padding: 9px; font-size: 13px; border-radius: 8px;">
								🚀 تجربة وفتح شاشة الطلب مباشرة 🔗
							</a>
						</div>

						<div style="font-size: 10px; color: #64748b; word-break: break-all; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #f1f5f9;">
							${data.delivery_url}
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
						<h3 style="margin: 0; color: #0284c7;">🔥 تسليم الغاز</h3>
						<h2 style="margin: 6px 0; font-size: 20px;">${data.customer_name || ''}</h2>
						${data.address_title ? `<h3 style="margin: 4px 0; color: #10b981;">🏢 ${data.address_title}</h3>` : ''}
						${data.address_line ? `<p style="margin: 4px 0; font-size: 12px; color: #64748b;">📍 ${data.address_line} ${data.city || ''}</p>` : ''}
						<div style="margin: 12px auto; max-width: 200px;">${data.qr_svg}</div>
						<div style="font-size: 10px; color: #64748b; word-break: break-all;">${data.delivery_url}</div>
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
