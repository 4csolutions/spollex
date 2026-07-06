# Copyright (c) 2026, 4C Solutions and contributors
# For license information, please see license.txt

import frappe

def update_renewal_lost_status(doc, method=None):
    if not doc.custom_renewed_sales_invoice:
        return

    # Check if the Quotation is marked as Lost
    is_lost = 1 if doc.status == "Lost" else 0
    frappe.db.set_value("Sales Invoice", doc.custom_renewed_sales_invoice, "custom_lost", is_lost)
