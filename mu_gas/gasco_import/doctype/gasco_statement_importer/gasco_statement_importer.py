# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
import json
import os


class GascoStatementImporter(Document):
	pass


@frappe.whitelist()
def preview_excel_data(importer_name):
	"""Parses uploaded GASCO statement Excel file and produces clean HTML table preview."""
	doc = frappe.get_doc("Gasco Statement Importer", importer_name)
	if not doc.excel_file:
		frappe.throw(_("Please upload an Excel file first."))

	file_doc = frappe.get_doc("File", {"file_url": doc.excel_file})
	file_path = file_doc.get_full_path()

	rows = _parse_gasco_excel(file_path)
	if not rows:
		frappe.throw(_("Could not extract any valid withdrawal data from this Excel file."))

	html = """
	<div class="table-responsive">
		<table class="table table-bordered table-sm text-center">
			<thead class="thead-light">
				<tr>
					<th>#</th>
					<th>Date</th>
					<th>Invoice / Order #</th>
					<th>Tank / Station</th>
					<th>Quantity (KG / L)</th>
					<th>Total Amount</th>
				</tr>
			</thead>
			<tbody>
	"""
	for i, r in enumerate(rows, 1):
		html += f"""
			<tr>
				<td>{i}</td>
				<td>{r.get('date', '')}</td>
				<td>{r.get('ref_no', '')}</td>
				<td>{r.get('tank', '')}</td>
				<td><b>{flt(r.get('qty', 0)):,.2f}</b></td>
				<td><b>{flt(r.get('amount', 0)):,.2f}</b></td>
			</tr>
		"""
	html += "</tbody></table></div>"

	doc.db_set({
		"status": "Previewed",
		"preview_html": html
	})

	return {
		"success": True,
		"rows_count": len(rows),
		"message": _("Extracted {0} transactions from GASCO statement.").format(len(rows))
	}


@frappe.whitelist()
def process_and_create_invoices(importer_name):
	"""Creates Purchase Invoices and Payment Entries automatically for each GASCO statement row."""
	doc = frappe.get_doc("Gasco Statement Importer", importer_name)
	if not doc.excel_file:
		frappe.throw(_("Please upload an Excel file first."))

	file_doc = frappe.get_doc("File", {"file_url": doc.excel_file})
	file_path = file_doc.get_full_path()

	rows = _parse_gasco_excel(file_path)
	if not rows:
		frappe.throw(_("No data found to process."))

	company = doc.company or frappe.defaults.get_user_default("Company")
	created_pi = []
	created_pe = []

	for r in rows:
		date_val = r.get("date") or nowdate()
		qty = flt(r.get("qty"))
		amount = flt(r.get("amount"))
		ref_no = r.get("ref_no") or ""
		rate = amount / qty if qty > 0 else 0

		# 1. Purchase Invoice
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = doc.supplier
		pi.company = company
		pi.posting_date = date_val
		pi.bill_no = ref_no
		pi.bill_date = date_val
		pi.update_stock = 1
		pi.set_warehouse = doc.warehouse

		pi.append("items", {
			"item_code": doc.item_code,
			"qty": qty,
			"rate": rate,
			"warehouse": doc.warehouse
		})

		pi.remarks = _("GASCO Statement Import: Ref {0} Tank {1}").format(ref_no, r.get("tank", ""))
		pi.insert(ignore_permissions=True)
		pi.submit()
		created_pi.append(pi.name)

		# 2. Payment Entry
		if doc.payment_account and amount > 0:
			pe = frappe.new_doc("Payment Entry")
			pe.payment_type = "Pay"
			pe.party_type = "Supplier"
			pe.party = doc.supplier
			pe.company = company
			pe.posting_date = date_val
			pe.paid_from = doc.payment_account
			pe.paid_to = pi.credit_to
			pe.paid_amount = amount
			pe.received_amount = amount
			pe.reference_no = ref_no
			pe.reference_date = date_val

			pe.append("references", {
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"total_amount": amount,
				"outstanding_amount": 0,
				"allocated_amount": amount
			})

			pe.insert(ignore_permissions=True)
			pe.submit()
			created_pe.append(pe.name)

	doc.db_set({
		"status": "Processed"
	})

	return {
		"success": True,
		"purchase_invoices": created_pi,
		"payment_entries": created_pe,
		"message": _("Created {0} Purchase Invoices and {1} Payment Entries successfully!").format(
			len(created_pi), len(created_pe)
		)
	}


def _parse_gasco_excel(file_path):
	import openpyxl
	wb = openpyxl.load_workbook(file_path, data_only=True)
	sheet = wb.active

	rows = []
	for row_idx in range(2, sheet.max_row + 1):
		c_date = sheet.cell(row=row_idx, column=1).value
		c_ref = sheet.cell(row=row_idx, column=2).value
		c_tank = sheet.cell(row=row_idx, column=3).value
		c_qty = sheet.cell(row=row_idx, column=4).value
		c_amount = sheet.cell(row=row_idx, column=5).value

		if not c_qty and not c_amount:
			continue

		rows.append({
			"date": str(c_date)[:10] if c_date else nowdate(),
			"ref_no": str(c_ref or "").strip(),
			"tank": str(c_tank or "").strip(),
			"qty": flt(c_qty),
			"amount": flt(c_amount)
		})

	return rows
