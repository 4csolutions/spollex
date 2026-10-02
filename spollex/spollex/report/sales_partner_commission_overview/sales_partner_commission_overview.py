# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

from frappe import _
from frappe.utils import flt
from erpnext.selling.report.sales_partner_commission_summary.sales_partner_commission_summary import (
	SalesPartnerCommissionSummaryReport,
)


def execute(filters=None):
	if not filters:
		filters = {}

	return SpollexSalesPartnerCommissionOverviewReport(filters).run()


class SpollexSalesPartnerCommissionOverviewReport(SalesPartnerCommissionSummaryReport):
	def prepare_columns(self):
		super().prepare_columns()

		# Add custom tax deduction and commission payable columns
		self.make_column(
			label=_("Tax Deduction(9%)"),
			fieldname="tax_deduction",
			fieldtype="Currency",
			width=120,
		)
		self.make_column(
			label=_("Commission Payable"),
			fieldname="commission_payable",
			fieldtype="Currency",
			width=120,
		)

	def get_data(self):
		super().get_data()

		# Compute tax deduction and commission payable for each row
		for row in self.data:
			total_commission = flt(row.get("total_commission", 0.0))
			tax_deduction = flt(total_commission * 0.09)
			commission_payable = flt(total_commission - tax_deduction)

			row["tax_deduction"] = tax_deduction
			row["commission_payable"] = commission_payable