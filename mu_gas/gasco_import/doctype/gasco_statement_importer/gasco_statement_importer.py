# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import os
import openpyxl
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class GascoStatementImporter(Document):
	pass


def _get_local_file_path(file_url):
	if not file_url:
		return None
	if file_url.startswith("/private/"):
		return frappe.get_site_path("private", file_url.replace("/private/", "", 1))
	if file_url.startswith("/files/"):
		return frappe.get_site_path("public", "files", file_url.replace("/files/", "", 1))
	return frappe.get_site_path(file_url.lstrip("/"))


def parse_gasco_rows(file_path):
	"""Parses GASCO Excel sheet and extracts rows intelligently."""
	wb = openpyxl.load_workbook(file_path, data_only=True)
	sheet = wb.active

	rows = list(sheet.iter_rows(values_only=True))
	if not rows:
		return []

	# Find header row
	header_idx = -1
	for idx, row in enumerate(rows[:15]):
		row_str = " ".join([str(c or "").lower() for c in row])
		if any(k in row_str for k in ["تاريخ", "date", "فاتورة", "invoice", "كمية", "qty", "مبلغ", "amount", "وزن"]):
			header_idx = idx
			break

	if header_idx == -1:
		header_idx = 0

	headers = [str(c or "").strip() for c in rows[header_idx]]
	parsed = []

	# Map columns by keyword
	col_map = {}
	for c_idx, h in enumerate(headers):
		hl = h.lower()
		if any(k in hl for k in ["تاريخ", "date"]) and "date" not in col_map:
			col_map["date"] = c_idx
		elif any(k in hl for k in ["فاتورة", "مستند", "invoice", "doc"]) and "invoice" not in col_map:
			col_map["invoice"] = c_idx
		elif any(k in hl for k in ["كمية", "وزن", "qty", "weight", "طن", "كجم", "لتر"]) and "qty" not in col_map:
			col_map["qty"] = c_idx
		elif any(k in hl for k in ["سعر", "rate", "price"]) and "rate" not in col_map:
			col_map["rate"] = c_idx
		elif any(k in hl for k in ["إجمالي", "مبلغ", "قيمة", "amount", "total"]) and "amount" not in col_map:
			col_map["amount"] = c_idx
		elif any(k in hl for k in ["صهريج", "خزان", "شاحنة", "tank", "truck"]) and "tank" not in col_map:
			col_map["tank"] = c_idx

	for r_idx, r in enumerate(rows[header_idx + 1:], start=header_idx + 2):
		if not any(r):
			continue

		date_val = r[col_map["date"]] if "date" in col_map and col_map["date"] < len(r) else None
		if not date_val:
			continue

		inv_val = r[col_map["invoice"]] if "invoice" in col_map and col_map["invoice"] < len(r) else f"GASCO-{r_idx}"
		qty_val = flt(r[col_map["qty"]]) if "qty" in col_map and col_map["qty"] < len(r) else 0.0
		amt_val = flt(r[col_map["amount"]]) if "amount" in col_map and col_map["amount"] < len(r) else 0.0
		rate_val = flt(r[col_map["rate"]]) if "rate" in col_map and col_map["rate"] < len(r) else 0.0
		tank_val = str(r[col_map["tank"]] or "") if "tank" in col_map and col_map["tank"] < len(r) else ""

		if qty_val > 0 and amt_val > 0 and rate_val == 0:
			rate_val = round(amt_val / qty_val, 4)
		elif rate_val > 0 and qty_val > 0 and amt_val == 0:
			amt_val = round(rate_val * qty_val, 2)

		if qty_val > 0 or amt_val > 0:
			try:
				parsed_date = getdate(date_val)
			except Exception:
				parsed_date = nowdate()

			parsed.append({
				"row_idx": r_idx,
				"date": parsed_date,
				"invoice_no": str(inv_val).strip(),
				"qty": qty_val,
				"rate": rate_val,
				"amount": amt_val,
				"tank": tank_val
			})

	return parsed


@frappe.whitelist()
def preview_excel_data(importer_name):
	"""Reads attached file and generates preview HTML table."""
	doc = frappe.get_doc("Gasco Statement Importer", importer_name)
	if not doc.excel_file:
		frappe.throw(_("يرجى إرفاق ملف إكسل كشف غازكو أولاً."))

	file_path = _get_local_file_path(doc.excel_file)
	if not file_path or not os.path.exists(file_path):
		frappe.throw(_("الملف المرفق غير موجود على السيرفر."))

	rows = parse_gasco_rows(file_path)
	if not rows:
		frappe.throw(_("لم يتم العثور على سطور بيانات صالحة داخل ملف الإكسل. يرجى التأكد من محتوى الشيت."))

	table_rows = "".join([f"""
		<tr class="hover:bg-slate-50 border-b text-xs">
			<td class="p-2 font-bold">{r['row_idx']}</td>
			<td class="p-2">{r['date']}</td>
			<td class="p-2 font-semibold text-blue-700">{r['invoice_no']}</td>
			<td class="p-2 text-slate-600">{r['tank']}</td>
			<td class="p-2 font-bold text-slate-800">{r['qty']}</td>
			<td class="p-2">{r['rate']}</td>
			<td class="p-2 font-bold text-emerald-700">{r['amount']:,.2f} ريال</td>
		</tr>
	""" for r in rows])

	total_amount = sum(r['amount'] for r in rows)
	total_qty = sum(r['qty'] for r in rows)

	html = f"""
	<div class="overflow-x-auto border rounded-xl p-3 bg-white">
		<div class="flex justify-between items-center mb-3 bg-slate-50 p-3 rounded-lg border">
			<span class="text-xs font-bold text-slate-700">عدد العمليات المستخرجة: <b class="text-blue-600">{len(rows)}</b></span>
			<span class="text-xs font-bold text-slate-700">إجمالي الكمية: <b class="text-slate-900">{total_qty:,.2f}</b></span>
			<span class="text-xs font-bold text-slate-700">إجمالي المبالغ: <b class="text-emerald-700">{total_amount:,.2f} ريال</b></span>
		</div>
		<table class="w-full text-right border-collapse">
			<thead>
				<tr class="bg-slate-100 text-slate-700 text-xs font-bold border-b">
					<th class="p-2">#</th>
					<th class="p-2">التاريخ</th>
					<th class="p-2">رقم الفاتورة/السند</th>
					<th class="p-2">الصهريج/الخزان</th>
					<th class="p-2">الكمية</th>
					<th class="p-2">السعر</th>
					<th class="p-2">المبلغ الإجمالي</th>
				</tr>
			</thead>
			<tbody>
				{table_rows}
			</tbody>
		</table>
	</div>
	"""

	doc.db_set("preview_html", html)
	return {"success": True, "count": len(rows), "total_amount": total_amount}


@frappe.whitelist()
def process_and_create_invoices(importer_name):
	"""Generates Purchase Invoices and linked Payment Entries for each parsed GASCO row."""
	doc = frappe.get_doc("Gasco Statement Importer", importer_name)
	file_path = _get_local_file_path(doc.excel_file)
	rows = parse_gasco_rows(file_path)
	if not rows:
		frappe.throw(_("لا توجد سطور قابلة للاستيراد."))

	company = doc.company
	supplier = doc.supplier
	warehouse = doc.warehouse
	item_code = doc.item_code
	payment_acc = doc.payment_account

	created_pi = []
	created_pe = []

	for r in rows:
		# 1. Create Purchase Invoice
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.bill_no = r["invoice_no"]
		pi.bill_date = r["date"]
		pi.posting_date = r["date"]
		pi.set_warehouse = warehouse

		pi.append("items", {
			"item_code": item_code,
			"qty": flt(r["qty"]),
			"rate": flt(r["rate"]),
			"warehouse": warehouse
		})

		pi.remarks = _("فاتورة مشتريات غازكو مستوردة من كشف الإكسل {0} - صهريج {1}").format(
			doc.name, r.get("tank", "")
		)

		pi.insert(ignore_permissions=True)
		pi.submit()
		created_pi.append(pi.name)

		# 2. Create Payment Entry (if payment account provided)
		if payment_acc:
			try:
				from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
				pe = get_payment_entry("Purchase Invoice", pi.name, bank_account=payment_acc)
				pe.posting_date = r["date"]
				pe.reference_no = r["invoice_no"]
				pe.reference_date = r["date"]
				pe.remarks = _("سداد مسحوبات غازكو فاتورة {0}").format(pi.name)
				pe.insert(ignore_permissions=True)
				pe.submit()
				created_pe.append(pe.name)
			except Exception as e:
				frappe.log_error(f"Failed to auto-create payment entry for {pi.name}: {e}", "GASCO Auto Payment")

	doc.status = "تم الاستيراد والتحويل"
	doc.save(ignore_permissions=True)

	return {
		"success": True,
		"invoices_count": len(created_pi),
		"payments_count": len(created_pe),
		"message": _("تم بنجاح توليد {0} فاتورة مشتريات لغازكو و {1} سند سداد دفعات.").format(
			len(created_pi), len(created_pe)
		)
	}
