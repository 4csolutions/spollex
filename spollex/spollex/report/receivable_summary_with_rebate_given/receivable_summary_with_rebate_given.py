# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

from erpnext.accounts.report.accounts_receivable_summary import accounts_receivable_summary
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	AccountsReceivableSummary as ERPNextAccountsReceivableSummary,
)
from frappe import _
from spollex.spollex.report.accounts_receivable_with_rebate_given.accounts_receivable_with_rebate_given import (
	SpollexReceivablePayableReport,
)


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return SpollexAccountsReceivableSummary(filters).run(args)


class SpollexAccountsReceivableSummary(ERPNextAccountsReceivableSummary):
	def get_columns(self):
		super().get_columns()

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

		if self.filters.sales_partner and self.account_type == "Receivable":
			for c in self.columns:
				if c.get("fieldname") == "sales_partner":
					c["fieldname"] = "default_sales_partner"

	def init_party_total(self, row):
		super().init_party_total(row)
		self.party_total[row.party]["rebate_received"] = 0.0
		self.party_total[row.party]["rebate_given"] = 0.0

	def set_party_details(self, row):
		super().set_party_details(row)
		if self.filters.sales_partner:
			self.party_total[row.party]["default_sales_partner"] = row.get(
				"default_sales_partner", ""
			)

	def get_data(self, args):
		orig_rp = accounts_receivable_summary.ReceivablePayableReport
		accounts_receivable_summary.ReceivablePayableReport = SpollexReceivablePayableReport
		try:
			super().get_data(args)
		finally:
			accounts_receivable_summary.ReceivablePayableReport = orig_rp


AccountsReceivableSummary = SpollexAccountsReceivableSummary