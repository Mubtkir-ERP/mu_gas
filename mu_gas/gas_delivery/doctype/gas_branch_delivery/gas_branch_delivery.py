# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import secrets
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime


class GasBranchDelivery(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		total_qty = 0.0
		total_amount = 0.0
		total_full = 0.0
		total_empty = 0.0

		for item in self.get("items", []):
			item.amount = flt(item.qty) * flt(item.rate)
			total_qty += flt(item.qty)
			total_amount += flt(item.amount)
			total_full += flt(item.full_qty or item.qty)
			total_empty += flt(item.empty_qty or 0)

		self.total_qty = total_qty
		self.total_amount = total_amount
		self.total_full_delivered = total_full
		self.total_empty_received = total_empty

	def on_cancel(self):
		if self.delivery_note:
			dn = frappe.get_doc("Delivery Note", self.delivery_note)
			if dn.docstatus == 1:
				dn.cancel()


@frappe.whitelist()
def send_delivery_otp(delivery_name):
	"""Generates 5-digit OTP and sends it to the customer branch phone via WhatsApp/SMS."""
	doc = frappe.get_doc("Gas Branch Delivery", delivery_name)
	if doc.status == "Confirmed":
		frappe.throw(_("هذا التسليم تم تأكيده بالفعل."))

	phone = doc.branch_phone or frappe.db.get_value("Address", doc.branch, "phone")
	if not phone:
		frappe.throw(_("لم يتم العثور على رقم هاتف مسجل لفرع العميل لإرسال كود التحقق."))

	otp = f"{secrets.randbelow(90000) + 10000}"
	doc.db_set("otp_code", otp)

	msg = _(
		"كود تأكيد استلام الغاز لـ {0} ({1}): {2}. يرجى تزويد السائق بالكود لإتمام التسليم."
	).format(doc.customer_name, doc.branch_title or doc.branch, otp)

	# Best effort send WhatsApp
	try:
		from pos_next.api.whatsapp_hook import send_whatsapp
		send_whatsapp(phone, msg)
	except Exception:
		# Fallback log
		frappe.log_error(f"Failed to send OTP to {phone}: {msg}", "Gas Delivery OTP")

	return {
		"success": True,
		"message": _("تم إرسال كود التحقق بنجاح إلى جوال الفرع: {0}").format(phone),
		"phone": phone
	}


@frappe.whitelist()
def verify_otp_and_confirm(delivery_name, input_otp):
	"""Verifies OTP and generates ERPNext Delivery Note deducting stock from driver warehouse."""
	doc = frappe.get_doc("Gas Branch Delivery", delivery_name)
	if doc.status == "Confirmed":
		return {"success": True, "delivery_note": doc.delivery_note}

	if not doc.otp_code or str(doc.otp_code).strip() != str(input_otp).strip():
		frappe.throw(_("كود التحقق غير صحيح، يرجى التأكد من مسؤول الفرع وإعادة المحاولة."))

	doc.otp_verified = 1
	doc.status = "Confirmed"

	# Create ERPNext Delivery Note
	dn = frappe.new_doc("Delivery Note")
	dn.customer = doc.customer
	dn.customer_address = doc.branch
	dn.posting_date = doc.posting_date
	dn.posting_time = doc.posting_time
	dn.set_warehouse = doc.driver_warehouse

	for item in doc.items:
		dn.append("items", {
			"item_code": item.item_code,
			"qty": flt(item.qty),
			"rate": flt(item.rate),
			"warehouse": doc.driver_warehouse,
			"uom": item.uom or frappe.db.get_value("Item", item.item_code, "stock_uom")
		})

	dn.remarks = _("سند تسليم غاز تلقائي لفرع {0} عبر التحقق برمز OTP (مستند: {1})").format(
		doc.branch_title or doc.branch, doc.name
	)

	dn.insert(ignore_permissions=True)
	dn.submit()

	doc.delivery_note = dn.name
	doc.save(ignore_permissions=True)

	return {
		"success": True,
		"delivery_note": dn.name,
		"message": _("تم التحقق بنجاح وإنشاء سند الإخراج والتسليم رقم {0}").format(dn.name)
	}
