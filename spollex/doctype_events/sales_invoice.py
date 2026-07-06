# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

import frappe

def update_renewal_invoice_status(doc, method=None):
    if not doc.custom_renewed_sales_invoice:
        return

    is_renewed = 1 if method == "on_submit" else 0
    frappe.db.set_value("Sales Invoice", doc.custom_renewed_sales_invoice, "custom_renewed", is_renewed)
