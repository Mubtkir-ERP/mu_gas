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
									company_name: data.company_name,
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
	const displayTitle = data.address_title
		? `<div style="font-size: 16px; font-weight: 800; color: #0f172a; margin-top: 2px;">🏢 ${data.address_title}</div>`
		: `<div style="font-size: 17px; font-weight: 800; color: #0f172a;">${data.customer_name || ''}</div>`;
	const printTitle = data.address_title
		? `<h2 style="margin: 6px 0; font-size: 20px; color: #0f172a;">🏢 ${data.address_title}</h2>`
		: `<h2 style="margin: 6px 0; font-size: 22px; color: #0f172a;">${data.customer_name || ''}</h2>`;

	let d = new frappe.ui.Dialog({
		title: title || __("رمز QR لتسليم الغاز"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "qr_card",
				options: `
					<div class="text-center p-3 border rounded bg-white shadow-sm" style="max-width: 350px; margin: 0 auto; direction: rtl;">
						${data.company_name ? `<div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px;">${data.company_name}</div>` : ''}
						<div style="font-size: 13px; font-weight: bold; color: #0284c7; margin-bottom: 4px;">🔥 تسليم الغاز</div>
						${displayTitle}
						${data.address_line ? `<div style="font-size: 11px; color: #64748b; margin-top: 2px;">📍 ${data.address_line} ${data.city || ''}</div>` : ''}
						
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

						<div style="font-size: 11px; color: #64748b; text-align: center; margin-top: 8px; font-weight: 600;">Powered By Mubtkir ERP</div>
					</div>
				`
			}
		],
		primary_action_label: __("طباعة الملصق 🖨️"),
		primary_action() {
			let printContents = `
				<div class="a6-sticker">
					<div class="a6-card">
						<div class="a6-header">
							${data.company_name ? `<div class="company-name">${data.company_name}</div>` : ''}
							<h3 class="gas-title">🔥 تسليم الغاز</h3>
							${printTitle}
							${data.address_line ? `<p class="address-line">📍 ${data.address_line} ${data.city || ''}</p>` : ''}
						</div>
						<div class="qr-box">${data.qr_svg}</div>
						<div class="a6-footer">Powered By Mubtkir ERP</div>
					</div>
				</div>
			`;
			let w = window.open('', '_blank', 'width=450,height=650');
			w.document.write(`
				<html>
					<head>
						<title>ملصق QR</title>
						<style>
							@page { size: A6 portrait; margin: 0; }
							* { box-sizing: border-box; }
							body { margin: 0; padding: 0; font-family: sans-serif; direction: rtl; width: 105mm; height: 148mm; }
							.a6-sticker { width: 105mm; height: 148mm; padding: 6mm; display: flex; align-items: stretch; justify-content: center; }
							.a6-card { width: 100%; border: 2px solid #0f172a; border-radius: 10px; padding: 6mm; display: flex; flex-direction: column; justify-content: space-between; align-items: center; text-align: center; }
							.a6-header { width: 100%; }
							.company-name { font-size: 16px; font-weight: 800; color: #0f172a; margin-bottom: 4px; }
							.gas-title { margin: 0 0 6px 0; color: #0284c7; font-size: 15px; }
							.address-line { margin: 4px 0 0 0; font-size: 12px; color: #64748b; }
							.qr-box { width: 58mm; height: 58mm; display: flex; align-items: center; justify-content: center; margin: 4mm auto; }
							.qr-box svg, .qr-box img { width: 100% !important; height: 100% !important; }
							.a6-footer { width: 100%; text-align: center; font-size: 11px; font-weight: 600; color: #475569; padding-top: 4px; border-top: 1px dashed #cbd5e1; }
						</style>
					</head>
					<body>${printContents}</body>
				</html>
			`);
			w.document.close();
			w.focus();
			setTimeout(() => { w.print(); }, 400);
		}
	});
	d.show();
}
