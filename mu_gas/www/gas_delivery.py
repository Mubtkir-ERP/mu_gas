# -*- coding: utf-8 -*-
import frappe
from frappe import _

def get_context(context):
	customer = frappe.form_dict.get("customer")
	branch = frappe.form_dict.get("branch")

	if not customer and not branch and frappe.form_dict.get("code"):
		# In case scanned content is MUBTKIR_BRANCH::{customer}::{branch}
		raw = frappe.form_dict.get("code")
		if "::" in raw:
			parts = raw.split("::")
			if len(parts) >= 3:
				customer = parts[1]
				branch = parts[2]

	context.customer = customer
	context.branch = branch

	if customer:
		context.customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	else:
		context.customer_name = ""

	if branch:
		addr = frappe.db.get_value("Address", branch, ["address_title", "address_line1", "city", "phone"], as_dict=True)
		context.branch_title = addr.address_title if addr else branch
		context.branch_line = addr.address_line1 if addr else ""
		context.branch_city = addr.city if addr else ""
		context.branch_phone = addr.phone if addr else ""
	else:
		context.branch_title = ""
		context.branch_line = ""
		context.branch_city = ""
		context.branch_phone = ""

	# Fetch driver default warehouse
	user = frappe.session.user
	user_wh = frappe.db.get_value("POS Profile", {"user": user}, "warehouse") or ""
	context.default_warehouse = user_wh

	# Common gas items
	context.gas_items = frappe.db.sql("""
		select name, item_name, standard_rate, stock_uom
		from `tabItem`
		where is_sales_item = 1 and disabled = 0
		order by modified desc limit 30
	""", as_dict=True)
