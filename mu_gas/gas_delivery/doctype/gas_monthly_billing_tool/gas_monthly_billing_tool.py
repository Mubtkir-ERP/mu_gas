# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class GasMonthlyBillingTool(Document):
	pass


@frappe.whitelist()
def generate_monthly_invoices(customer, from_date, to_date, billing_mode, company=None):
	"""Generates consolidated monthly Sales Invoices for unbilled Gas Deliveries."""
	if not customer:
		frappe.throw(_("Please select customer first."))

	deliveries = frappe.db.sql("""
		SELECT name, branch, branch_title, delivery_note, posting_date
		FROM `tabGas Branch Delivery`
		WHERE customer = %s
		  AND posting_date BETWEEN %s AND %s
		  AND status = 'Confirmed'
		  AND (sales_invoice IS NULL OR sales_invoice = '')
		ORDER BY posting_date ASC
	""", (customer, from_date, to_date), as_dict=True)

	if not deliveries:
		frappe.throw(_("No confirmed unbilled deliveries found for this customer in period ({0} to {1}).").format(from_date, to_date))

	company = company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

	created_invoices = []

	if "Per Branch" in billing_mode or "لكل فرع" in billing_mode:
		# Group by branch
		branch_groups = {}
		for d in deliveries:
			branch_groups.setdefault(d.branch, []).append(d)

		for branch, d_list in branch_groups.items():
			si = _create_invoice_for_deliveries(customer, branch, d_list, company, to_date)
			created_invoices.append(si.name)
	else:
		# Consolidated for all branches
		si = _create_invoice_for_deliveries(customer, None, deliveries, company, to_date)
		created_invoices.append(si.name)

	return {
		"success": True,
		"invoices": created_invoices,
		"message": _("Successfully created {0} consolidated Sales Invoice(s): {1}").format(
			len(created_invoices), ", ".join(created_invoices)
		)
	}


def _create_invoice_for_deliveries(customer, branch, delivery_list, company, posting_date):
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	if branch:
		si.customer_address = branch
	si.company = company
	si.posting_date = posting_date or nowdate()
	si.due_date = si.posting_date

	delivery_names = [d.name for d in delivery_list]
	delivery_notes = [d.delivery_note for d in delivery_list if d.delivery_note]

	# Fetch all items from the Gas Branch Delivery Item child tables
	items = frappe.db.sql("""
		SELECT 
			di.item_code, 
			di.item_name, 
			di.uom, 
			SUM(di.qty) as total_qty, 
			di.rate
		FROM `tabGas Branch Delivery Item` di
		JOIN `tabGas Branch Delivery` d ON d.name = di.parent
		WHERE d.name IN %(deliveries)s
		GROUP BY di.item_code, di.rate
	""", {"deliveries": tuple(delivery_names)}, as_dict=True)

	for itm in items:
		si.append("items", {
			"item_code": itm.item_code,
			"qty": flt(itm.total_qty),
			"rate": flt(itm.rate) or frappe.db.get_value("Item", itm.item_code, "standard_rate") or 0,
			"uom": itm.uom or frappe.db.get_value("Item", itm.item_code, "stock_uom")
		})

	si.remarks = _("Consolidated Gas Sales Invoice for period up to {0} covering deliveries: {1}").format(
		posting_date, ", ".join(delivery_names[:10]) + ("..." if len(delivery_names) > 10 else "")
	)

	si.insert(ignore_permissions=True)

	# Update the delivery records to link this Sales Invoice
	for d in delivery_list:
		frappe.db.set_value("Gas Branch Delivery", d.name, {
			"sales_invoice": si.name,
			"status": "Invoiced"
		}, update_modified=False)

	return si
