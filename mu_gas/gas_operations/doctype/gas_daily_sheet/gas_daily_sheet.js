frappe.ui.form.on("Gas Daily Sheet", {
	setup(frm) {
		frm.set_query("expense_account", "expenses", function() {
			return {
				filters: {
					company: frm.doc.company,
					root_type: "Expense",
					is_group: 0
				}
			};
		});

		frm.set_query("van_warehouse", function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});
	},

	refresh(frm) {
		if ((frm.doc.status === "Draft" || frm.doc.status === "مسودة") && !frm.is_new()) {
			frm.add_custom_button(__("Submit to Accountant 📤"), () => {
				frm.set_value("status", "Submitted to Accountant");
				frm.save();
			}).addClass("btn-secondary");
		}

		if (frm.doc.status === "Submitted to Accountant" || frm.doc.status === "مرسل للمحاسب") {
			frm.add_custom_button(__("Approve Sheet & Generate Entries ⚡"), () => {
				frappe.confirm(
					__("Are you sure you want to approve this sheet and generate Sales Invoices and Journal Entries?"),
					() => {
						frappe.call({
							method: "mu_gas.gas_operations.doctype.gas_daily_sheet.gas_daily_sheet.approve_and_generate_entries",
							args: { sheet_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Generating invoices and journal entries..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.msgprint({
										title: __("Approval Completed"),
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

frappe.ui.form.on("Gas Daily Sheet Expense", {
	amount(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.total_amount = flt(row.amount) + flt(row.tax_amount || 0);
		frm.refresh_field("expenses");
		calculate_sheet_totals(frm);
	},
	tax_amount(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.total_amount = flt(row.amount) + flt(row.tax_amount || 0);
		frm.refresh_field("expenses");
		calculate_sheet_totals(frm);
	},
	expenses_remove(frm) {
		calculate_sheet_totals(frm);
	}
});

frappe.ui.form.on("Gas Daily Sheet Sale", {
	qty(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.amount = flt(row.qty) * flt(row.rate || 0);
		frm.refresh_field("sales");
		calculate_sheet_totals(frm);
	},
	rate(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.amount = flt(row.qty) * flt(row.rate || 0);
		frm.refresh_field("sales");
		calculate_sheet_totals(frm);
	},
	sales_remove(frm) {
		calculate_sheet_totals(frm);
	}
});

function calculate_sheet_totals(frm) {
	let total_sales = 0.0;
	let total_expenses = 0.0;

	(frm.doc.sales || []).forEach(s => {
		total_sales += flt(s.amount);
	});

	(frm.doc.expenses || []).forEach(e => {
		total_expenses += flt(e.total_amount || (flt(e.amount) + flt(e.tax_amount || 0)));
	});

	frm.set_value("total_sales", total_sales);
	frm.set_value("total_expenses", total_expenses);
	frm.set_value("net_cash", total_sales - total_expenses);
}
