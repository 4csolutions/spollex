# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
import datetime

from erpnext.setup.doctype.sales_person.sales_person import SalesPerson

class CustomSalesPerson(SalesPerson):
    def get_incentive_amount(self, allocated_amount_against_invoice, allocated_amount):
        total_incentive = 0
        remaining_amount = allocated_amount
        slabs = self.get("custom_incentive_slabs")

        for slab in slabs:
            slab_start = slab.from_amount
            slab_end = slab.to_amount

            if slab_end == 0 and allocated_amount_against_invoice > slab_start:
                total_incentive += slab.incentive_percent * remaining_amount * 0.01

            if slab_start <= allocated_amount_against_invoice < slab_end:
                amount_in_this_slab = min(slab_end - allocated_amount_against_invoice, remaining_amount)
                total_incentive +=  slab.incentive_percent * amount_in_this_slab * 0.01
                remaining_amount -= amount_in_this_slab
                allocated_amount_against_invoice += amount_in_this_slab

            if remaining_amount == 0:
                break
            elif remaining_amount > 0 and allocated_amount_against_invoice >= slab_end:
                if allocated_amount_against_invoice == slab_end:
                    allocated_amount_against_invoice = slab_end + 1
                continue

        return total_incentive
    
@frappe.whitelist()
def fetch_commission_rate(sales_person_name, allocated_amount, posting_date):
    sales_person = frappe.get_doc("Sales Person", sales_person_name)
    allocated_amount = flt(allocated_amount)

    posting_date = datetime.datetime.strptime(posting_date, '%Y-%m-%d').date()
    fiscal_year_start = datetime.date(posting_date.year, 1, 1)
    fiscal_year_end = datetime.date(posting_date.year, 12, 31)

    allocated_amount_against_invoice = (
        frappe.db.sql("""
            SELECT SUM(st.allocated_amount)
            FROM `tabSales Team` st, `tabSales Invoice` si
            WHERE st.parent = si.name
            AND si.docstatus = 1
            AND si.posting_date BETWEEN %s AND %s
            AND st.sales_person = %s
        """, (fiscal_year_start, fiscal_year_end, sales_person_name))[0][0] or 0.0
    )

    incentives = sales_person.get_incentive_amount(allocated_amount_against_invoice, allocated_amount)

    commission_rate = (incentives * 100)/allocated_amount

    return commission_rate