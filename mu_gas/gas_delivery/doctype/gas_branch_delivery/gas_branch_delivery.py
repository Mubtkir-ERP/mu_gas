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
def create_branch_delivery(customer, items, driver_warehouse, branch=None, sales_order=None):
	"""Creates a Gas Branch Delivery record and dispatches OTP in a single clean transaction."""
	if not customer:
		frappe.throw(_("Customer is required."))

	if isinstance(items, str):
		import json
		items = json.loads(items)

	if not items:
		frappe.throw(_("At least one item is required for delivery."))

	doc = frappe.new_doc("Gas Branch Delivery")
	doc.customer = customer
	doc.branch = branch or None
	doc.sales_order = sales_order or None
	doc.driver_warehouse = driver_warehouse
	doc.driver = frappe.session.user
	doc.status = "Pending OTP"

	for itm in items:
		doc.append("items", {
			"item_code": itm.get("item_code"),
			"qty": flt(itm.get("qty", 1)),
			"full_qty": flt(itm.get("full_qty", itm.get("qty", 1))),
			"empty_qty": flt(itm.get("empty_qty", 0)),
			"rate": flt(itm.get("rate", 0)),
			"so_detail": itm.get("so_detail")
		})

	doc.insert(ignore_permissions=True)
	otp_res = send_delivery_otp(doc.name)

	return {
		"success": True,
		"delivery_name": doc.name,
		"otp_message": otp_res.get("message")
	}


@frappe.whitelist()
def send_delivery_otp(delivery_name):
	"""Generates 5-digit OTP and sends it to customer/branch phone via WhatsApp."""
	doc = frappe.get_doc("Gas Branch Delivery", delivery_name)
	if doc.status == "Confirmed":
		frappe.throw(_("This delivery has already been confirmed."))

	phone = doc.branch_phone
	if not phone and doc.branch:
		phone = frappe.db.get_value("Address", doc.branch, "phone")
	if not phone and doc.customer:
		phone = frappe.db.get_value("Customer", doc.customer, "mobile_no")
		if not phone:
			# Search primary contact phone
			contact_name = frappe.db.get_value(
				"Dynamic Link",
				{"link_doctype": "Customer", "link_name": doc.customer, "parenttype": "Contact"},
				"parent"
			)
			if contact_name:
				phone = frappe.db.get_value("Contact", contact_name, "mobile_no") or frappe.db.get_value("Contact", contact_name, "phone")

	if not phone:
		frappe.throw(_("No phone number registered for customer or branch to send OTP."))

	otp = f"{secrets.randbelow(90000) + 10000}"
	doc.db_set("otp_code", otp)

	recipient_desc = doc.branch_title or doc.customer_name or doc.customer
	msg = _(
		"Gas delivery confirmation code for {0}: {1}. Please provide this code to the driver."
	).format(recipient_desc, otp)

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
		"message": _("Verification code sent successfully to: {0}").format(phone)
	}


@frappe.whitelist()
def verify_otp_and_confirm(delivery_name, input_otp):
	"""
	Verifies 5-digit OTP and generates:
	1. Standard ERPNext Sales Order (طلب مبيعات)
	2. Standard ERPNext Delivery Note (أمر تسليم) linked to the Sales Order and deducting stock from driver's warehouse.
	"""
	doc = frappe.get_doc("Gas Branch Delivery", delivery_name)
	if doc.status == "Confirmed":
		frappe.throw(_("This delivery has already been confirmed."))

	if str(doc.otp_code).strip() != str(input_otp).strip():
		frappe.throw(_("Invalid OTP code. Please verify the code sent to the customer."))

	posting_date = doc.posting_date or frappe.utils.nowdate()
	company = getattr(doc, "company", None) or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

	# Step 1: Create and Submit Sales Order (طلب مبيعات)
	so = frappe.new_doc("Sales Order")
	so.customer = doc.customer
	if doc.branch:
		so.customer_address = doc.branch
		so.shipping_address_name = doc.branch
	so.company = company
	so.transaction_date = posting_date
	so.delivery_date = posting_date
	so.set_warehouse = doc.driver_warehouse
	so.remarks = _("Gas QR Delivery - Customer {0} (Driver: {1})").format(
		doc.customer_name or doc.customer, doc.driver or ""
	)

	for itm in doc.items:
		so.append("items", {
			"item_code": itm.item_code,
			"qty": flt(itm.qty),
			"rate": flt(itm.rate),
			"warehouse": doc.driver_warehouse,
			"uom": itm.uom or frappe.db.get_value("Item", itm.item_code, "stock_uom"),
			"delivery_date": posting_date
		})

	# Set standard ERPNext taxes and totals
	so.run_method("set_missing_values")
	so.run_method("calculate_taxes_and_totals")
	so.insert(ignore_permissions=True)
	so.submit()

	# Step 2: Create and Submit Delivery Note (أمر تسليم) against the created Sales Order
	dn = frappe.new_doc("Delivery Note")
	dn.customer = doc.customer
	if doc.branch:
		dn.customer_address = doc.branch
		dn.shipping_address_name = doc.branch
	dn.company = company
	dn.set_warehouse = doc.driver_warehouse
	dn.posting_date = posting_date
	dn.posting_time = doc.posting_time or frappe.utils.now_datetime().strftime("%H:%M:%S")
	dn.against_sales_order = so.name
	dn.remarks = _("Gas Delivery via Driver {0} - Confirmed by Branch OTP (Against SO: {1})").format(
		doc.driver or "", so.name
	)

	# Map so items to delivery note items
	so_items_dict = {item.item_code: item.name for item in so.items}

	for itm in doc.items:
		item_row = {
			"item_code": itm.item_code,
			"qty": flt(itm.qty),
			"uom": itm.uom or frappe.db.get_value("Item", itm.item_code, "stock_uom"),
			"warehouse": doc.driver_warehouse,
			"rate": flt(itm.rate) or 0,
			"against_sales_order": so.name,
			"so_detail": so_items_dict.get(itm.item_code)
		}
		dn.append("items", item_row)

	# Set standard ERPNext defaults and taxes (Strictly system standard)
	dn.run_method("set_missing_values")
	dn.run_method("calculate_taxes_and_totals")
	dn.insert(ignore_permissions=True)
	dn.submit()

	doc.db_set({
		"otp_verified": 1,
		"status": "Confirmed",
		"sales_order": so.name,
		"delivery_note": dn.name
	})

	return {
		"success": True,
		"sales_order": so.name,
		"delivery_note": dn.name,
		"message": _("Delivery confirmed successfully! Sales Order {0} and Delivery Note {1} created.").format(
			so.name, dn.name
		)
	}
