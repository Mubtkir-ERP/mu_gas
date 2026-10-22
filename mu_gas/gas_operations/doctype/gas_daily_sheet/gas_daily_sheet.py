# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate


class GasDailySheet(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		total_s = 0.0
		for row in self.get("sales", []):
			row.amount = flt(row.qty) * flt(row.rate)
			total_s += flt(row.amount)

		total_e = 0.0
		for row in self.get("expenses", []):
			total_e += flt(row.amount)

		self.total_sales = total_s
		self.total_expenses = total_e
		self.net_cash = total_s - total_e


@frappe.whitelist()
def approve_and_generate_entries(sheet_name):
	"""Accountant approval: automatically generates Sales Invoices and Expense Journal Entries."""
	doc = frappe.get_doc("Gas Daily Sheet", sheet_name)
	if doc.status == "معتمد وتم توليد العمليات":
		frappe.throw(_("تم اعتماد هذا المسير بالفعل سابقاً."))

	created_invoices = []
	created_expense_entries = []
	company = doc.company or frappe.defaults.get_user_default("Company")

	# 1. Generate Sales Invoices for sales
	for s in doc.sales:
		si = frappe.new_doc("Sales Invoice")
		si.customer = s.customer
		if s.branch:
			si.customer_address = s.branch
		si.company = company
		si.posting_date = doc.posting_date
		si.set_warehouse = doc.van_warehouse

		si.append("items", {
			"item_code": s.item_code,
			"qty": flt(s.qty),
			"rate": flt(s.rate),
			"warehouse": doc.van_warehouse
		})

		si.remarks = _("فاتورة مبيعات غاز مولدة آلياً من المسير اليومي {0} للسائق {1}").format(
			doc.name, doc.driver
		)

		if s.payment_method in ["نقدي", "شبكة مدى"]:
			si.is_pos = 1
			# Get payment mode
			mop = "Cash" if s.payment_method == "نقدي" else "Mada"
			if not frappe.db.exists("Mode of Payment", mop):
				mop = frappe.db.get_value("Mode of Payment", {"type": "Cash"}) or "Cash"
			si.append("payments", {
				"mode_of_payment": mop,
				"amount": flt(s.amount)
			})

		si.insert(ignore_permissions=True)
		si.submit()
		created_invoices.append(si.name)

	# 2. Generate Journal Entry for expenses
	if doc.expenses:
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = company
		je.posting_date = doc.posting_date
		je.user_remark = _("قيد إثبات مصاريف المسير اليومي {0} للسائق {1}").format(doc.name, doc.driver)

		cash_account = doc.cash_account or frappe.db.get_value("Company", company, "default_cash_account")

		for exp in doc.expenses:
			# Debit: Expense Account
			je.append("accounts", {
				"account": exp.expense_account,
				"debit_in_account_currency": flt(exp.amount),
				"user_remark": f"{exp.expense_type}: {exp.remarks or ''} {exp.receipt_reference or ''}"
			})

		# Credit: Cash Account
		je.append("accounts", {
			"account": cash_account,
			"credit_in_account_currency": flt(doc.total_expenses),
			"user_remark": _("صرف نقدية عهدة السائق {0}").format(doc.driver)
		})

		je.insert(ignore_permissions=True)
		je.submit()
		created_expense_entries.append(je.name)

	# Update sheet doc
	doc.status = "معتمد وتم توليد العمليات"
	doc.accountant_user = frappe.session.user
	doc.accountant_approval_date = now_datetime()
	doc.save(ignore_permissions=True)

	msg = _("تم بنجاح اعتماد المسير اليومي! تم إنشاء {0} فاتورة مبيعات، وقيد مصاريف {1}.").format(
		len(created_invoices), ", ".join(created_expense_entries) if created_expense_entries else "بدون مصاريف"
	)

	return {
		"success": True,
		"invoices": created_invoices,
		"expense_entries": created_expense_entries,
		"message": msg
	}
