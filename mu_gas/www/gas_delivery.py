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

	context.customer = customer
	context.branch = branch

	# Customer Details
	if customer:
		context.customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
		cust_phone = frappe.db.get_value("Customer", customer, "mobile_no") or ""
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
		context.branch_title = "العميل الرئيسي (تسليم مباشر بدون فرع)"
		context.branch_line = ""
		context.branch_city = ""
		context.branch_phone = cust_phone
		context.has_branch = False

	# Fetch Active Sales Orders (طلبات المبيعات النشطة المفتوحة للتسليم)
	active_sales_orders = []
	so_items_map = {}

	if customer:
		so_query = """
			SELECT name, transaction_date, grand_total, status, customer_address
			FROM `tabSales Order`
			WHERE customer = %(customer)s
			  AND docstatus = 1
			  AND status IN ('To Deliver and Bill', 'To Deliver')
		"""
		params = {"customer": customer}
		if branch:
			so_query += " AND (customer_address = %(branch)s OR customer_address IS NULL OR customer_address = '')"
			params["branch"] = branch

		so_query += " ORDER BY transaction_date DESC LIMIT 10"
		active_sales_orders = frappe.db.sql(so_query, params, as_dict=True)

		if active_sales_orders:
			so_names = [so.name for so in active_sales_orders]
			so_items = frappe.db.sql("""
				SELECT 
					soi.name as so_detail,
					soi.parent as sales_order,
					soi.item_code,
					soi.item_name,
					(soi.qty - soi.delivered_qty) as pending_qty,
					soi.rate,
					soi.uom
				FROM `tabSales Order Item` soi
				WHERE soi.parent IN %(so_names)s
				  AND (soi.qty - soi.delivered_qty) > 0
			""", {"so_names": tuple(so_names)}, as_dict=True)

			for itm in so_items:
				so_items_map.setdefault(itm.sales_order, []).append({
					"so_detail": itm.so_detail,
					"item_code": itm.item_code,
					"item_name": itm.item_name,
					"qty": flt(itm.pending_qty),
					"rate": flt(itm.rate),
					"uom": itm.uom or ""
				})

	context.active_sales_orders = active_sales_orders
	context.so_items_json = json.dumps(so_items_map)

	# Fetch driver default warehouse
	user = frappe.session.user
	user_wh = frappe.db.get_value("POS Profile", {"user": user}, "warehouse") or ""
	context.default_warehouse = user_wh

	# Common gas items for direct manual delivery
	context.gas_items = frappe.db.sql("""
		SELECT name, item_name, standard_rate, stock_uom
		FROM `tabItem`
		WHERE is_sales_item = 1 AND disabled = 0
		ORDER BY modified DESC LIMIT 30
	""", as_dict=True)
