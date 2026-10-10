# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb, scrub
from frappe.utils import cstr, getdate, nowdate
from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
	ReceivablePayableReport as ERPNextReceivablePayableReport,
)


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return SpollexReceivablePayableReport(filters).run(args)


class SpollexReceivablePayableReport(ERPNextReceivablePayableReport):
	def get_columns(self):
		super().get_columns()
		col_fieldnames = [c.get("fieldname") for c in self.columns]

		# Insert purchase_order before bill_no if Payable
		if self.account_type == "Payable" and "purchase_order" not in col_fieldnames:
			po_col = dict(
				label=_("Purchase Order"),
				fieldname="purchase_order",
				fieldtype="Data",
				width=180,
			)
			if "bill_no" in col_fieldnames:
				idx = col_fieldnames.index("bill_no")
				self.columns.insert(idx, po_col)
			else:
				self.columns.append(po_col)

		# Insert rebate columns after credit_note
		col_fieldnames = [c.get("fieldname") for c in self.columns]
		if "credit_note" in col_fieldnames:
			idx = col_fieldnames.index("credit_note")
			if self.account_type == "Receivable" and "rebate_given" not in col_fieldnames:
				self.columns.insert(
					idx + 1,
					dict(
						label=_("Rebate Given"),
						fieldname="rebate_given",
						fieldtype="Currency",
						options="currency",
						width=120,
					),
				)
			elif self.account_type == "Payable" and "rebate_received" not in col_fieldnames:
				self.columns.insert(
					idx + 1,
					dict(
						label=_("Rebate Received"),
						fieldname="rebate_received",
						fieldtype="Currency",
						options="currency",
						width=120,
					),
				)

		# Insert Days Until PDC and adjust labels if show_future_payments
		if self.filters.show_future_payments:
			for c in self.columns:
				if c.get("fieldname") == "future_ref":
					c["label"] = _("PDC Payment Ref")
				elif c.get("fieldname") == "future_amount":
					c["label"] = _("PDC Payment Amount")

			col_fieldnames = [c.get("fieldname") for c in self.columns]
			if "remaining_balance" in col_fieldnames and "days_until_pdc" not in col_fieldnames:
				idx = col_fieldnames.index("remaining_balance")
				self.columns.insert(
					idx + 1,
					dict(
						label=_("Days Until PDC"),
						fieldname="days_until_pdc",
						fieldtype="Int",
						width=120,
					),
				)

		# Default sales partner fieldname mapping
		if self.filters.sales_partner and self.filters.account_type == "Receivable":
			for c in self.columns:
				if c.get("fieldname") == "sales_partner":
					c["fieldname"] = "default_sales_partner"

	def get_invoice_details(self):
		super().get_invoice_details()

		if self.account_type == "Receivable":
			default_receivable_account = frappe.db.get_value(
				"Company", self.filters.company, "default_receivable_account"
			)
			for inv_name, d in self.invoice_details.items():
				credit_note_total = frappe.db.sql(
					"""
					select sum(`tabJournal Entry Account`.credit_in_account_currency)
					from `tabJournal Entry Account`
					join `tabJournal Entry` on `tabJournal Entry`.name = `tabJournal Entry Account`.parent
					where `tabJournal Entry Account`.parent in (
						select `tabJournal Entry Account`.parent
						from `tabJournal Entry Account`
						where `tabJournal Entry Account`.reference_name = %s
						and `tabJournal Entry Account`.docstatus = 1
					)
					and `tabJournal Entry Account`.account = %s
					and `tabJournal Entry Account`.docstatus = 1
					and `tabJournal Entry`.voucher_type = 'Credit Note';
					""",
					(inv_name, default_receivable_account),
				)
				credit_note_total = credit_note_total[0][0] or 0 if credit_note_total else 0
				d["rebate_given"] = credit_note_total

		elif self.account_type == "Payable":
			default_payable_account = frappe.db.get_value(
				"Company", self.filters.company, "default_payable_account"
			)
			for inv_name, pi in self.invoice_details.items():
				po = frappe.db.get_all(
					"Purchase Invoice Item",
					filters={"parent": inv_name},
					fields=["distinct purchase_order"],
				)
				po_list = [
					f'<a href="/app/purchase-order/{p.purchase_order}" style="display:block; text-align:left;">{p.purchase_order}</a>'
					for p in po
					if p.purchase_order
				]

				debit_note_total = frappe.db.sql(
					"""
					select sum(`tabJournal Entry Account`.debit_in_account_currency)
					from `tabJournal Entry Account`
					where `tabJournal Entry Account`.parent in (
						select `tabJournal Entry Account`.parent
						from `tabJournal Entry Account`
						where `tabJournal Entry Account`.reference_name = %s
						and `tabJournal Entry Account`.docstatus = 1
					)
					and `tabJournal Entry Account`.account = %s
					and `tabJournal Entry Account`.docstatus = 1
					""",
					(inv_name, default_payable_account),
				)
				debit_note_total = debit_note_total[0][0] or 0 if debit_note_total else 0
				pi["rebate_received"] = debit_note_total
				pi["purchase_order"] = ", ".join(po_list)

	def set_invoice_details(self, row):
		super().set_invoice_details(row)

		invoice_details = self.invoice_details.get(row.voucher_no, {})
		if "rebate_received" in invoice_details:
			row["rebate_received"] = invoice_details["rebate_received"]
			row["paid"] = row["paid"] - row["rebate_received"]
		elif "rebate_given" in invoice_details:
			row["rebate_given"] = invoice_details["rebate_given"]
			row["paid"] = row["paid"] - row["rebate_given"]

	def allocate_future_payments(self, row):
		super().allocate_future_payments(row)

		if self.filters.show_future_payments:
			row.days_until_pdc = 0
			for future in self.future_payments.get((row.voucher_no, row.party), []):
				if future.future_date:
					row.days_until_pdc = max((getdate(future.future_date) - getdate(nowdate())).days, 0)
					break

	def build_data(self):
		# Spollex only considers Sales Invoices and Purchase Invoices
		for _key, row in list(self.voucher_balance.items()):
			if row.voucher_type not in ("Sales Invoice", "Purchase Invoice"):
				self.voucher_balance.pop(_key, None)

		super().build_data()


# Export alias for backwards compatibility
ReceivablePayableReport = SpollexReceivablePayableReport
