# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import io
import urllib.parse


def build_delivery_url(site_url, customer, branch=None):
	"""Constructs a standard, RFC 3986-compliant URL with proper encoding for QR scanning."""
	base = (site_url or "").rstrip("/")
	params = {"customer": customer or ""}
	if branch:
		params["branch"] = branch
	encoded_query = urllib.parse.urlencode(params)
	return f"{base}/gas-delivery?{encoded_query}"


def generate_qr_image_or_svg(content):
	"""Generates an SVG or data URI for the given text content."""
	try:
		import qrcode
		from qrcode.image.svg import SvgPathImage
		qr = qrcode.QRCode(
			version=None,
			error_correction=qrcode.constants.ERROR_CORRECT_M,
			box_size=10,
			border=2,
			image_factory=SvgPathImage
		)
		qr.add_data(content)
		qr.make(fit=True)
		img = qr.make_image()
		stream = io.BytesIO()
		img.save(stream)
		return stream.getvalue().decode("utf-8")
	except Exception:
		# Fallback if qrcode library is missing in environment
		encoded = urllib.parse.quote(content, safe="")
		return f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}" alt="QR Code" style="width:220px;height:220px;" />'


@frappe.whitelist()
def get_customer_delivery_qr(customer=None, address=None):
	"""
	Generates Gas Delivery QR Code for:
	- Customer with no branches -> Single QR for customer
	- Customer with branches / Address -> QR for specific branch
	All URLs are URL-encoded so mobile cameras and scanners open the browser directly.
	"""
	site_url = frappe.utils.get_url()

	if address:
		# Address-specific QR
		addr_doc = frappe.get_doc("Address", address)
		linked_customer = customer
		if not linked_customer:
			linked_customer = frappe.db.get_value(
				"Dynamic Link",
				{"parent": address, "parenttype": "Address", "link_doctype": "Customer"},
				"link_name"
			)

		customer_name = frappe.db.get_value("Customer", linked_customer, "customer_name") if linked_customer else ""
		delivery_url = build_delivery_url(site_url, linked_customer, address)
		qr_svg = generate_qr_image_or_svg(delivery_url)

		return {
			"has_branches": True,
			"customer": linked_customer,
			"customer_name": customer_name,
			"address": address,
			"address_title": addr_doc.address_title or address,
			"address_line": addr_doc.address_line1 or "",
			"city": addr_doc.city or "",
			"phone": addr_doc.phone or "",
			"delivery_url": delivery_url,
			"readable_url": f"{site_url}/gas-delivery?customer={linked_customer or ''}&branch={address}",
			"qr_svg": qr_svg
		}

	if customer:
		customer_doc = frappe.get_doc("Customer", customer)
		# Check if customer has addresses (branches)
		branches = frappe.db.sql("""
			SELECT dl.parent as address, a.address_title, a.address_line1, a.city, a.phone
			FROM `tabDynamic Link` dl
			JOIN `tabAddress` a ON a.name = dl.parent
			WHERE dl.link_doctype = 'Customer'
			  AND dl.link_name = %s
			  AND dl.parenttype = 'Address'
		""", (customer,), as_dict=True)

		if not branches:
			# Customer without branches: Generate single customer QR
			delivery_url = build_delivery_url(site_url, customer)
			qr_svg = generate_qr_image_or_svg(delivery_url)
			return {
				"has_branches": False,
				"customer": customer,
				"customer_name": customer_doc.customer_name or customer,
				"mobile_no": customer_doc.mobile_no or "",
				"delivery_url": delivery_url,
				"readable_url": f"{site_url}/gas-delivery?customer={customer}",
				"qr_svg": qr_svg
			}
		else:
			# Customer has branches: list each branch with its QR code
			branch_list = []
			for b in branches:
				b_url = build_delivery_url(site_url, customer, b.address)
				b_svg = generate_qr_image_or_svg(b_url)
				branch_list.append({
					"address": b.address,
					"address_title": b.address_title or b.address,
					"address_line": b.address_line1 or "",
					"city": b.city or "",
					"phone": b.phone or "",
					"delivery_url": b_url,
					"readable_url": f"{site_url}/gas-delivery?customer={customer}&branch={b.address}",
					"qr_svg": b_svg
				})

			return {
				"has_branches": True,
				"customer": customer,
				"customer_name": customer_doc.customer_name or customer,
				"branches": branch_list
			}

	frappe.throw(_("Please provide Customer or Address."))
