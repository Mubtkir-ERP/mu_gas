# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
import os


class GascoStatementImporter(Document):
	pass


@frappe.whitelist()
def reconcile_statement_with_invoices(importer_name):
	"""
	Reconciles GASCO Excel statement against manual Purchase Invoices entered by staff in ERPNext.
	Matches by Supplier, Bill No (Invoice #), Date, and Amount to prevent duplicates without creating redundant entries.
	"""
	doc = frappe.get_doc("Gasco Statement Importer", importer_name)
	if not doc.excel_file:
		frappe.throw(_("Please upload an Excel file first."))

	file_doc = frappe.get_doc("File", {"file_url": doc.excel_file})
	file_path = file_doc.get_full_path()

	rows = _parse_gasco_excel(file_path)
	if not rows:
		frappe.throw(_("Could not extract any valid data from this Excel file."))

	company = doc.company or frappe.defaults.get_user_default("Company")
	supplier = doc.supplier

	# Fetch existing manual Purchase Invoices for this supplier and company (non-cancelled)
	existing_invoices = frappe.db.sql("""
		SELECT name, bill_no, posting_date, grand_total, net_total, status, docstatus, remarks
		FROM `tabPurchase Invoice`
		WHERE supplier = %s
		  AND company = %s
		  AND docstatus != 2
		ORDER BY posting_date DESC
	""", (supplier, company), as_dict=True)

	# Build lookup maps
	# 1. By exact bill_no (normalized)
	pi_by_bill_no = {}
	for pi in existing_invoices:
		b_no = (pi.bill_no or "").strip().lower()
		if b_no:
			pi_by_bill_no.setdefault(b_no, []).append(pi)

	# Set to track claimed Purchase Invoices to ensure 1-to-1 matching and strictly prevent duplication
	claimed_pi = set()

	doc.items = []
	matched_count = 0
	missing_count = 0
	discrepancy_count = 0
	total_statement_amount = 0.0
	total_matched_amount = 0.0

	for r in rows:
		ref_no = str(r.get("ref_no") or "").strip()
		stmt_date = r.get("date")
		stmt_qty = flt(r.get("qty"))
		stmt_amount = flt(r.get("amount"))
		tank = str(r.get("tank") or "").strip()

		total_statement_amount += stmt_amount

		matched_pi = None
		match_status = "Missing in ERPNext"
		inv_amount = 0.0
		diff = 0.0

		# Attempt 1: Match by Bill No (رقم الفاتورة / أمر التوريد)
		if ref_no:
			norm_ref = ref_no.lower()
			if norm_ref in pi_by_bill_no:
				for candidate in pi_by_bill_no[norm_ref]:
					if candidate.name not in claimed_pi:
						matched_pi = candidate
						break

		# Attempt 2: If not matched by bill_no, search by date and amount (tolerance <= 1.0)
		if not matched_pi and stmt_date and stmt_amount > 0:
			for candidate in existing_invoices:
				if candidate.name in claimed_pi:
					continue
				c_date = str(candidate.posting_date)
				c_total = flt(candidate.grand_total)
				if c_date == str(stmt_date) and abs(c_total - stmt_amount) <= 1.0:
					matched_pi = candidate
					break

		if matched_pi:
			claimed_pi.add(matched_pi.name)
			inv_amount = flt(matched_pi.grand_total)
			diff = stmt_amount - inv_amount

			if abs(diff) <= 0.05:
				match_status = "Matched"
				matched_count += 1
				total_matched_amount += inv_amount
			else:
				match_status = "Discrepancy"
				discrepancy_count += 1
				total_matched_amount += inv_amount
		else:
			match_status = "Missing in ERPNext"
			missing_count += 1

		doc.append("items", {
			"statement_date": stmt_date,
			"ref_no": ref_no,
			"tank": tank,
			"qty": stmt_qty,
			"statement_amount": stmt_amount,
			"match_status": match_status,
			"purchase_invoice": matched_pi.name if matched_pi else None,
			"invoice_amount": inv_amount,
			"difference": diff
		})

	# Generate HTML Summary Report
	html = _generate_reconciliation_html(
		len(rows), matched_count, missing_count, discrepancy_count,
		total_statement_amount, total_matched_amount, doc.items
	)

	doc.total_rows = len(rows)
	doc.matched_rows = matched_count
	doc.missing_rows = missing_count
	doc.discrepancy_rows = discrepancy_count
	doc.total_statement_amount = total_statement_amount
	doc.total_matched_amount = total_matched_amount
	doc.status = "Reconciled"
	doc.preview_html = html
	doc.save(ignore_permissions=True)

	return {
		"success": True,
		"total_rows": len(rows),
		"matched_rows": matched_count,
		"missing_rows": missing_count,
		"discrepancy_rows": discrepancy_count,
		"message": _("Reconciliation completed: {0} matched, {1} missing, {2} with discrepancies.").format(
			matched_count, missing_count, discrepancy_count
		)
	}


def _generate_reconciliation_html(total, matched, missing, discrepancy, stmt_total, matched_total, items):
	html = f"""
	<div class="row my-3">
		<div class="col-sm-3">
			<div class="card p-3 text-center bg-light border-0 shadow-sm">
				<span class="text-muted small">إجمالي عمليات الكشف</span>
				<h4 class="font-weight-bold text-dark my-1">{total}</h4>
				<small class="text-secondary">{stmt_total:,.2f} ر.س</small>
			</div>
		</div>
		<div class="col-sm-3">
			<div class="card p-3 text-center bg-success text-white border-0 shadow-sm">
				<span class="small">مطابق بالنظام ✔</span>
				<h4 class="font-weight-bold my-1">{matched}</h4>
				<small>{matched_total:,.2f} ر.س</small>
			</div>
		</div>
		<div class="col-sm-3">
			<div class="card p-3 text-center bg-danger text-white border-0 shadow-sm">
				<span class="small">غير مدخل بالنظام ✕</span>
				<h4 class="font-weight-bold my-1">{missing}</h4>
				<small>بحاجة لإدخال</small>
			</div>
		</div>
		<div class="col-sm-3">
			<div class="card p-3 text-center bg-warning text-dark border-0 shadow-sm">
				<span class="small">يوجد فرق بالقيمة ⚠️</span>
				<h4 class="font-weight-bold my-1">{discrepancy}</h4>
				<small>تتطلب مراجعة</small>
			</div>
		</div>
	</div>

	<div class="table-responsive mt-3">
		<table class="table table-bordered table-sm text-center table-hover">
			<thead class="thead-light">
				<tr>
					<th>#</th>
					<th>تاريخ الكشف</th>
					<th>رقم الفاتورة / الإشعار</th>
					<th>الصهريج / المحطة</th>
					<th>الكمية</th>
					<th>المبلغ بالكشف</th>
					<th>حالة المطابقة</th>
					<th>فاتورة المشتريات بالنظام</th>
					<th>مبلغ الفاتورة</th>
					<th>الفرق</th>
				</tr>
			</thead>
			<tbody>
	"""

	for idx, itm in enumerate(items, 1):
		status_badge = ""
		if itm.match_status == "Matched":
			status_badge = '<span class="badge badge-success px-2 py-1">مطابق ✔</span>'
		elif itm.match_status == "Discrepancy":
			status_badge = '<span class="badge badge-warning px-2 py-1">يوجد فرق ⚠️</span>'
		else:
			status_badge = '<span class="badge badge-danger px-2 py-1">غير مسجل بالنظام ✕</span>'

		pi_link = f"<a href='/app/purchase-invoice/{itm.purchase_invoice}' target='_blank'><b>{itm.purchase_invoice}</b></a>" if itm.purchase_invoice else "-"
		diff_str = f"{flt(itm.difference):,.2f}" if itm.difference else "0.00"

		html += f"""
			<tr>
				<td>{idx}</td>
				<td>{itm.statement_date or ''}</td>
				<td><b>{itm.ref_no or ''}</b></td>
				<td>{itm.tank or ''}</td>
				<td>{flt(itm.qty):,.2f}</td>
				<td>{flt(itm.statement_amount):,.2f}</td>
				<td>{status_badge}</td>
				<td>{pi_link}</td>
				<td>{flt(itm.invoice_amount):,.2f}</td>
				<td class="{'text-danger font-weight-bold' if abs(flt(itm.difference)) > 0.05 else ''}">{diff_str}</td>
			</tr>
		"""

	html += "</tbody></table></div>"
	return html


def _parse_gasco_excel(file_path):
	import openpyxl
	wb = openpyxl.load_workbook(file_path, data_only=True)
	sheet = wb.active

	# Dynamic Header Detection
	date_col = 1
	ref_col = 2
	tank_col = 3
	qty_col = 4
	amount_col = 5
	start_row = 2

	# Scan first 5 rows for header keywords
	for r in range(1, min(sheet.max_row + 1, 6)):
		for c in range(1, min(sheet.max_column + 1, 15)):
			val = str(sheet.cell(row=r, column=c).value or "").strip().lower()
			if any(k in val for k in ["تاريخ", "date"]):
				date_col = c
				start_row = r + 1
			elif any(k in val for k in ["فاتورة", "إشعار", "بوليصة", "order", "invoice", "ref"]):
				ref_col = c
			elif any(k in val for k in ["خزان", "صهريج", "محطة", "tank"]):
				tank_col = c
			elif any(k in val for k in ["كمية", "وزن", "qty", "weight"]):
				qty_col = c
			elif any(k in val for k in ["مبلغ", "إجمالي", "قيمة", "amount", "total"]):
				amount_col = c

	rows = []
	for row_idx in range(start_row, sheet.max_row + 1):
		c_date = sheet.cell(row=row_idx, column=date_col).value
		c_ref = sheet.cell(row=row_idx, column=ref_col).value
		c_tank = sheet.cell(row=row_idx, column=tank_col).value
		c_qty = sheet.cell(row=row_idx, column=qty_col).value
		c_amount = sheet.cell(row=row_idx, column=amount_col).value

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
