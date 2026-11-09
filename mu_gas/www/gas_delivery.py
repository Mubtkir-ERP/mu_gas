# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import flt
import urllib.parse
import json

no_cache = 1


def get_context(context):
	# Require authentication: Redirect Guest to login and preserve the destination URL
	if frappe.session.user == "Guest":
		req_path = getattr(frappe.local.request, "full_path", None) or "/gas-delivery"
		frappe.local.flags.redirect_location = f"/login?redirect-to={urllib.parse.quote(str(req_path))}"
		raise frappe.Redirect

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

	# Customer Details (Search by ID or Name safely)
	customer_name = ""
	cust_phone = ""
	if customer:
		customer_name = frappe.db.get_value("Customer", customer, "customer_name")
		if not customer_name:
			cust_id = frappe.db.get_value("Customer", {"customer_name": customer}, "name")
			if cust_id:
				customer = cust_id
				customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
			else:
				customer_name = customer

		cust_phone = frappe.db.get_value("Customer", customer, "mobile_no") or ""
		if not cust_phone:
			try:
				contact_name = frappe.db.get_value(
					"Dynamic Link",
					{"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
					"parent"
				)
				if contact_name:
					cust_phone = frappe.db.get_value("Contact", contact_name, "mobile_no") or frappe.db.get_value("Contact", contact_name, "phone") or ""
			except Exception:
				pass

	context.customer = customer or ""
	context.customer_name = customer_name or ""

	# Branch (Address) Details (Search by ID or Title safely)
	branch_title = ""
	branch_line = ""
	branch_city = ""
	branch_phone = ""
	has_branch = False

	if branch:
		addr = frappe.db.get_value(
			"Address", branch,
			["name", "address_title", "address_line1", "city", "phone"],
			as_dict=True
		)
		if not addr:
			addr = frappe.db.get_value(
				"Address", {"address_title": branch},
				["name", "address_title", "address_line1", "city", "phone"],
				as_dict=True
			)

		if addr:
			context.branch = addr.name
			context.branch_title = addr.address_title or addr.name
			context.branch_line = addr.address_line1 or ""
			context.branch_city = addr.city or ""
			context.branch_phone = addr.phone or cust_phone
			context.has_branch = True
		else:
			context.branch = branch
			context.branch_title = branch
			context.branch_line = ""
			context.branch_city = ""
			context.branch_phone = cust_phone
			context.has_branch = True
	else:
		context.branch = ""
		context.branch_title = "العميل الرئيسي (بدون فرع)"
		context.branch_line = ""
		context.branch_city = ""
		context.branch_phone = cust_phone
		context.has_branch = False

	# Fetch driver user info and default warehouse safely
	user = frappe.session.user
	context.driver_user = user
	context.driver_name = frappe.db.get_value("User", user, "full_name") or user

	user_wh = ""
	try:
		pos_user = frappe.db.get_value("POS Profile User", {"user": user}, "parent")
		if pos_user:
			user_wh = frappe.db.get_value("POS Profile", pos_user, "warehouse") or ""
	except Exception:
		pass

	if not user_wh:
		try:
			user_wh = frappe.db.get_value("User Permission", {"user": user, "allow": "Warehouse"}, "for_value") or ""
		except Exception:
			pass

	context.default_warehouse = user_wh or ""

	# Gas items available for sale with standard rates (cleanly serialized to avoid Decimal errors)
	clean_items = []
	try:
		raw_items = frappe.db.sql("""
			SELECT name, item_name, standard_rate, stock_uom
			FROM `tabItem`
			WHERE is_sales_item = 1 AND disabled = 0
			ORDER BY modified DESC LIMIT 50
		""", as_dict=True)

		for itm in raw_items:
			clean_items.append({
				"name": str(itm.name),
				"item_name": str(itm.item_name or itm.name),
				"standard_rate": flt(itm.standard_rate),
				"stock_uom": str(itm.stock_uom or "")
			})
	except Exception:
		pass

	context.gas_items = clean_items
	context.gas_items_json = json.dumps(clean_items, ensure_ascii=False)
