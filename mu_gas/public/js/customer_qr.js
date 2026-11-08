frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("رمز QR لتسليم الغاز 🏷️"), () => {
				frappe.call({
					method: "mu_gas.gas_delivery.qr_utils.get_customer_delivery_qr",
					args: { customer: frm.doc.name },
					freeze: true,
					freeze_message: __("جاري توليد رمز الـ QR..."),
					callback(r) {
						if (!r.message) return;
						let data = r.message;

						if (!data.has_branches) {
							// Single Customer QR (No branches)
							let d = new frappe.ui.Dialog({
								title: __("رمز QR لتسليم الغاز - {0}").replace("{0}", data.customer_name),
								fields: [
									{
										fieldtype: "HTML",
										fieldname: "qr_preview",
										options: `
											<div id="print-area" class="text-center p-4 border rounded bg-white shadow-sm" style="max-width: 320px; margin: 0 auto;">
												<div style="font-size: 14px; font-weight: bold; color: #1e293b; margin-bottom: 4px;">🔥 تسليم الغاز المباشر</div>
												<div style="font-size: 16px; font-weight: 800; color: #0f172a; margin-bottom: 2px;">${data.customer_name}</div>
												<div style="font-size: 11px; color: #64748b; margin-bottom: 12px;">كود العميل: ${data.customer}</div>
												<div style="display:flex; justify-content:center; align-items:center; margin-bottom: 10px;">
													${data.qr_svg}
												</div>
												<div style="font-size: 11px; color: #0284c7; font-weight: bold; word-break: break-all;">${data.delivery_url}</div>
												<div style="font-size: 10px; color: #94a3b8; margin-top: 8px;">امسح الكود بواسطة جوال السائق للبدء الفوري</div>
											</div>
										`
									}
								],
								primary_action_label: __("طباعة الملصق 🖨️"),
								primary_action() {
									let printContents = document.getElementById("print-area").innerHTML;
									let w = window.open('', '', 'width=450,height=600');
									w.document.write('<html><head><title>ملصق QR تسليم الغاز</title><style>body{font-family:sans-serif;direction:rtl;text-align:center;padding:20px;} img,svg{max-width:200px;margin:10px auto;display:block;}</style></head><body>' + printContents + '</body></html>');
									w.document.close();
									w.focus();
									setTimeout(() => { w.print(); w.close(); }, 300);
								}
							});
							d.show();
						} else {
							// Customer has branches: list all branches
							let rowsHtml = data.branches.map((b, idx) => `
								<div class="p-3 mb-2 border rounded d-flex justify-content-between align-items-center bg-white shadow-sm">
									<div>
										<div class="font-weight-bold text-dark">🏢 ${b.address_title}</div>
										<small class="text-muted">📍 ${b.address_line} ${b.city} | 📞 ${b.phone || 'بدون هاتف'}</small>
									</div>
									<button class="btn btn-sm btn-primary print-branch-btn" data-idx="${idx}">
										عرض وطباعة الـ QR 🏷️
									</button>
								</div>
							`).join("");

							let d = new frappe.ui.Dialog({
								title: __("رموز QR لفروع العميل: {0}").replace("{0}", data.customer_name),
								fields: [
									{
										fieldtype: "HTML",
										fieldname: "branches_list",
										options: `
											<div style="max-height: 400px; overflow-y: auto;">
												<p class="text-muted small">هذا العميل لديه فروع وعناوين متعددة. يتم توليد رمز QR مستقل لكل عنوان فرع:</p>
												${rowsHtml}
											</div>
										`
									}
								]
							});
							d.show();

							d.$wrapper.find('.print-branch-btn').on('click', function() {
								let idx = $(this).data('idx');
								let b = data.branches[idx];
								let printW = window.open('', '', 'width=450,height=600');
								let html = `
									<html>
									<head>
										<title>ملصق QR - ${b.address_title}</title>
										<style>
											body { font-family: sans-serif; direction: rtl; text-align: center; padding: 25px; }
											.sticker { border: 2px solid #000; border-radius: 12px; padding: 15px; }
											img, svg { max-width: 200px; margin: 10px auto; display: block; }
										</style>
									</head>
									<body>
										<div class="sticker">
											<h3>🔥 تسليم الغاز - فرع العميل</h3>
											<h2>${data.customer_name}</h2>
											<h4>🏢 ${b.address_title}</h4>
											<p>${b.address_line} ${b.city}</p>
											<div>${b.qr_svg}</div>
											<small>${b.delivery_url}</small>
										</div>
									</body>
									</html>
								`;
								printW.document.write(html);
								printW.document.close();
								printW.focus();
								setTimeout(() => { printW.print(); printW.close(); }, 300);
							});
						}
					}
				});
			}, __("الغاز"));
		}
	}
});

