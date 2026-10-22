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
		frappe.throw(_("This delivery has already been confirmed."))

	phone = doc.branch_phone or frappe.db.get_value("Address", doc.branch, "phone")
	if not phone:
		frappe.throw(_("No phone number registered for customer branch to send OTP."))

	otp = f"{secrets.randbelow(90000) + 10000}"
	doc.db_set("otp_code", otp)

	msg = _(
		"Gas delivery confirmation code for {0} ({1}): {2}. Please provide this code to the driver."
	).format(doc.customer_name, doc.branch_title or doc.branch, otp)

	try:
		if frappe.db.exists("DocType", "WhatsApp Message"):
			frappe.get_doc({
				"doctype": "WhatsApp Message",
				"to_number": phone,
				"message": msg
			}).insert(ignore_permissions=True)
	except Exception as err:
		frappe.log_error(f"Failed to send WhatsApp OTP: {err}", "Gas Delivery OTP")

	return {
		"success": True,
		"message": _("Verification code sent successfully to branch phone: {0}").format(phone)
	}


@frappe.whitelist()
def verify_otp_and_confirm(delivery_name, input_otp):
	"""Verifies 5-digit OTP and generates ERPNext Delivery Note automatically."""
	doc = frappe.get_doc("Gas Branch Delivery", delivery_name)
	if doc.status == "Confirmed":
		frappe.throw(_("This delivery has already been confirmed."))

	if str(doc.otp_code).strip() != str(input_otp).strip():
		frappe.throw(_("Invalid OTP code. Please verify the code sent to the customer branch."))

	# Create Delivery Note in ERPNext
	dn = frappe.new_doc("Delivery Note")
	dn.customer = doc.customer
	dn.customer_address = doc.branch
	dn.shipping_address_name = doc.branch
	dn.set_warehouse = doc.driver_warehouse
	dn.posting_date = doc.posting_date
	dn.posting_time = doc.posting_time
	dn.remarks = _("Gas Delivery via Driver {0} - Confirmed by Branch OTP").format(doc.driver or "")

	for itm in doc.items:
		dn.append("items", {
			"item_code": itm.item_code,
			"qty": flt(itm.qty),
			"uom": itm.uom or frappe.db.get_value("Item", itm.item_code, "stock_uom"),
			"warehouse": doc.driver_warehouse,
			"rate": flt(itm.rate) or 0
		})

	dn.insert(ignore_permissions=True)
	dn.submit()

	doc.db_set({
		"otp_verified": 1,
		"status": "Confirmed",
		"delivery_note": dn.name
	})

	return {
		"success": True,
		"delivery_note": dn.name,
		"message": _("Delivery confirmed successfully! Delivery Note {0} created.").format(dn.name)
	}
