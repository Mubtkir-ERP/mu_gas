# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class GasDailySheet(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		total_sales = 0.0
		total_expenses = 0.0

		for s in self.get("sales", []):
			s.amount = flt(s.qty) * flt(s.rate)
			total_sales += flt(s.amount)

		for e in self.get("expenses", []):
			total_expenses += flt(e.amount)

		self.total_sales = total_sales
		self.total_expenses = total_expenses
		self.net_cash = total_sales - total_expenses


@frappe.whitelist()
def approve_and_generate_entries(sheet_name):
	"""Approved by Accountant: Creates Sales Invoices and Journal Entry for expenses automatically."""
	sheet = frappe.get_doc("Gas Daily Sheet", sheet_name)
	if sheet.status in ["Approved & Generated", "معتمد وتم توليد العمليات"]:
		frappe.throw(_("This sheet has already been approved and processed."))

	company = sheet.company or frappe.defaults.get_user_default("Company")
	created_invoices = []

	# 1. Generate Sales Invoices for sales rows
	for row in sheet.sales:
		si = frappe.new_doc("Sales Invoice")
		si.customer = row.customer
		if row.branch:
			si.customer_address = row.branch
		si.company = company
		si.posting_date = sheet.posting_date
		si.due_date = sheet.posting_date
		si.set_warehouse = sheet.van_warehouse
		si.update_stock = 1

		si.append("items", {
			"item_code": row.item_code,
			"qty": flt(row.qty),
			"rate": flt(row.rate),
			"warehouse": sheet.van_warehouse
		})

		pm = str(row.payment_method or "")
		if "Cash" in pm or "نقدي" in pm:
			si.is_pos = 1
			si.append("payments", {
				"mode_of_payment": "Cash",
				"amount": flt(row.amount),
				"account": sheet.cash_account
			})

		si.remarks = _("Generated from Gas Daily Sheet: {0}").format(sheet.name)
		si.insert(ignore_permissions=True)
		si.submit()
		created_invoices.append(si.name)

	# 2. Generate Journal Entry for expenses
	je_name = None
	if sheet.expenses and flt(sheet.total_expenses) > 0:
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = company
		je.posting_date = sheet.posting_date
		je.user_remark = _("Daily Expenses from Gas Sheet {0} - Driver {1}").format(sheet.name, sheet.driver)

		for exp in sheet.expenses:
			if flt(exp.amount) > 0:
				# Debit Expense Account
				je.append("accounts", {
					"account": exp.expense_account,
					"debit_in_account_currency": flt(exp.amount),
					"user_remark": f"{exp.expense_type}: {exp.receipt_reference or ''} {exp.remarks or ''}".strip()
				})
				# Credit Driver Cash/Custody Account
				je.append("accounts", {
					"account": sheet.cash_account,
					"credit_in_account_currency": flt(exp.amount),
					"user_remark": f"Cash settlement: {sheet.driver}"
				})

		je.insert(ignore_permissions=True)
		je.submit()
		je_name = je.name

	sheet.db_set({
		"status": "Approved & Generated",
		"accountant_user": frappe.session.user,
		"accountant_approval_date": now_datetime(),
		"remarks": (sheet.remarks or "") + f"\nGenerated Invoices: {', '.join(created_invoices)}. Journal Entry: {je_name or 'None'}."
	})

	return {
		"success": True,
		"invoices": created_invoices,
		"journal_entry": je_name,
		"message": _("Sheet approved! Generated {0} Sales Invoices and Journal Entry {1}.").format(
			len(created_invoices), je_name or ""
		)
	}
