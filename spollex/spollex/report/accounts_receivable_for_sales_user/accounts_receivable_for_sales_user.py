# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.accounts_receivable import accounts_receivable
from spollex.spollex.report.accounts_receivable_with_rebate_given.accounts_receivable_with_rebate_given import (
	SpollexReceivablePayableReport,
)


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return AccountsReceivableForSalesUser(filters).run(args)


class AccountsReceivableForSalesUser(SpollexReceivablePayableReport):
	def prepare_ple_query(self):
		# Temporarily ignore PermissionError when building match conditions for Payment Ledger Entry,
		# because Sales User roles do not have direct read permission to raw Payment Ledger Entry.
		orig_build_qb = accounts_receivable.build_qb_match_conditions

		def safe_build_qb(doctype):
			try:
				return orig_build_qb(doctype)
			except frappe.PermissionError:
				return []

		accounts_receivable.build_qb_match_conditions = safe_build_qb
		try:
			super().prepare_ple_query()
		finally:
			accounts_receivable.build_qb_match_conditions = orig_build_qb

	def fetch_ple_in_buffered_cursor(self):
		self.ple_entries = self.ple_query.run(as_dict=True)
		self.filter_ple_entries_by_user_sales_person()

		for ple in self.ple_entries:
			self.init_voucher_balance(ple)

		for ple in self.ple_entries:
			self.update_voucher_balance(ple)

		delattr(self, "ple_entries")

	def fetch_ple_in_unbuffered_cursor(self):
		self.ple_entries = []
		with frappe.db.unbuffered_cursor():
			for ple in self.ple_query.run(as_dict=True, as_iterator=True):
				self.ple_entries.append(ple)

		self.filter_ple_entries_by_user_sales_person()

		for ple in self.ple_entries:
			self.init_voucher_balance(ple)

		for ple in self.ple_entries:
			self.update_voucher_balance(ple)

		delattr(self, "ple_entries")

	def filter_ple_entries_by_user_sales_person(self):
		current_user = frappe.session.user

		# Get sales person(s) mapped to this user (via 'custom_user_id' field in Sales Person)
		sales_persons = frappe.get_all(
			"Sales Person", filters={"custom_user_id": current_user}, pluck="name"
		)

		if not sales_persons:
			# No sales person found for the current user -> exclude all Sales Invoices
			self.ple_entries = [
				ple for ple in self.ple_entries if ple.voucher_type != "Sales Invoice"
			]
			return

		# Get Sales Invoice numbers where this sales person is in the Sales Team
		si_with_sales_person = frappe.db.sql(
			"""
			SELECT DISTINCT parent
			FROM `tabSales Team`
			WHERE parenttype = 'Sales Invoice' AND sales_person IN %s
			""",
			(sales_persons,),
			as_list=True,
		)

		allowed_si = {row[0] for row in si_with_sales_person}

		# Filter ple_entries
		self.ple_entries = [
			ple
			for ple in self.ple_entries
			if ple.voucher_type != "Sales Invoice" or ple.voucher_no in allowed_si
		]
