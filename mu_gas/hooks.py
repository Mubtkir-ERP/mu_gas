# -*- coding: utf-8 -*-
# Copyright (c) 2026, Mubtkir and contributors
# For license information, please see license.txt

app_name = "mu_gas"
app_title = "عمليات الغاز"
app_publisher = "Mubtkir"
app_description = "إدارة عمليات وتوزيع الغاز، تسليم فروع العملاء بالرمز السريع OTP، المسير واليومية الميدانية، واستيراد كشوفات غازكو"
app_email = "info@mubtkir.com"
app_license = "mit"
required_apps = ["erpnext"]

# Web Route for Mobile Driver QR Delivery
website_route_rules = [
	{"from_route": "/gas-delivery", "to_route": "gas_delivery"}
]

# Doctype JS injections
doctype_js = {
	"Customer": "public/js/customer_qr.js",
	"Address": "public/js/address_qr.js"
}

