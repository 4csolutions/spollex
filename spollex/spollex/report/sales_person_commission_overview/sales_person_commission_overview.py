# Copyright (c) 2024, 4C Solutions and contributors
# For license information, please see license.txt

from frappe import _
from frappe.utils import flt
from erpnext.selling.report.sales_person_commission_summary.sales_person_commission_summary import (
	execute as erpnext_execute,
	get_columns as erpnext_get_columns,
)


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	base_columns, base_data = erpnext_execute(filters)

	data = []
	if base_data:
		has_total_row = all(x == "" for x in base_data[-1])
		rows = base_data[:-1] if has_total_row else base_data

		for d in rows:
			incentives = flt(d[9])
			tax_deduction = flt(incentives * 0.09)
			incentives_payable = flt(incentives - tax_deduction)

			row = list(d) + [tax_deduction, incentives_payable]
			data.append(row)

		if has_total_row and data:
			total_row = [""] * len(data[0])
			data.append(total_row)

	return columns, data


def get_columns(filters):
	columns = erpnext_get_columns(filters)

	# Adjust width if needed to match custom styling
	for col in columns:
		if col.get("fieldname") == "contribution_percentage":
			col["width"] = 100
		elif col.get("fieldname") == "commission_rate":
			col["width"] = 100

	columns.extend(
		[
			{
				"label": _("Tax Deduction(9%)"),
				"fieldname": "tax_deduction",
				"fieldtype": "Currency",
				"width": 120,
			},
			{
				"label": _("Incentives Payable"),
				"fieldname": "incentives_payable",
				"fieldtype": "Currency",
				"width": 120,
			},
		]
	)

	return columns