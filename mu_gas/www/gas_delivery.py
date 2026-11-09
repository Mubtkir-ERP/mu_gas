# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import flt
import urllib.parse
import json


def get_context(context):
	customer = frappe.form_dict.get("customer")
	branch = frappe.form_dict.get("branch")
	raw_code = frappe.form_dict.get("code")

	if raw_code and (not customer or not branch):
		# If scanned QR is full URL
		if "http" in raw_code or "?" in raw_code:
			parsed = urllib.parse.urlparse(raw_code)
			qs = urllib.parse.parse_qs(parsed.query)
			if "customer" in qs and not customer:
				customer = qs["customer"][0]
			if "branch" in qs and not branch:
				branch = qs["branch"][0]
		elif "::" in raw_code:
			parts = raw_code.split("::")
			if len(parts) >= 2:
				customer = parts[1]
				if len(parts) >= 3 and parts[2]:
					branch = parts[2]

	if customer:
		customer = urllib.parse.unquote_plus(str(customer)).strip()
	if branch:
		branch = urllib.parse.unquote_plus(str(branch)).strip()

	context.customer = customer
	context.branch = branch

	# Customer Details
	if customer:
		context.customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
		cust_phone = frappe.db.get_value("Customer", customer, "mobile_no") or ""
		if not cust_phone:
			# Search primary contact phone
			contact_name = frappe.db.get_value(
				"Dynamic Link",
				{"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
				"parent"
			)
			if contact_name:
				cust_phone = frappe.db.get_value("Contact", contact_name, "mobile_no") or frappe.db.get_value("Contact", contact_name, "phone") or ""
	else:
		context.customer_name = ""
		cust_phone = ""

	# Branch (Address) Details
	if branch:
		addr = frappe.db.get_value(
			"Address", branch,
			["address_title", "address_line1", "city", "phone"],
			as_dict=True
		)
		context.branch_title = addr.address_title if addr else branch
		context.branch_line = addr.address_line1 if addr else ""
		context.branch_city = addr.city if addr else ""
		context.branch_phone = addr.phone if (addr and addr.phone) else cust_phone
		context.has_branch = True
	else:
		context.branch_title = "العميل الرئيسي (بدون فرع)"
		context.branch_line = ""
		context.branch_city = ""
		context.branch_phone = cust_phone
		context.has_branch = False

	# Fetch driver default warehouse
	user = frappe.session.user
	user_wh = frappe.db.get_value("POS Profile", {"user": user}, "warehouse") or ""
	context.default_warehouse = user_wh

	# Gas items available for sale with standard rates
	context.gas_items = frappe.db.sql("""
		SELECT name, item_name, standard_rate, stock_uom
		FROM `tabItem`
		WHERE is_sales_item = 1 AND disabled = 0
		ORDER BY modified DESC LIMIT 50
	""", as_dict=True)
