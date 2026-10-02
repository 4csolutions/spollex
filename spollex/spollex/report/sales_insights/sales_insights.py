# Copyright (c) 2025, 4C Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.selling.report.sales_analytics.sales_analytics import Analytics


def execute(filters=None):
	return SpollexAnalytics(filters).run()


class SpollexAnalytics(Analytics):
	def get_columns(self):
		super().get_columns()

		if self.filters.tree_type == "Item":
			# Find position of stock_uom to place item_group before it and stock_in_hand after it
			stock_uom_idx = None
			for idx, col in enumerate(self.columns):
				if col.get("fieldname") == "stock_uom":
					stock_uom_idx = idx
					break

			if stock_uom_idx is not None:
				self.columns.insert(
					stock_uom_idx,
					{
						"label": _("Item Group"),
						"fieldname": "item_group",
						"fieldtype": "Link",
						"options": "Item Group",
						"width": 100,
					},
				)
				# stock_uom is now at stock_uom_idx + 1
				self.columns.insert(
					stock_uom_idx + 2,
					{
						"label": _("Stock In Hand"),
						"fieldname": "stock_in_hand",
						"fieldtype": "Data",
						"width": 120,
					},
				)

	def get_rows(self):
		super().get_rows()

		if self.filters.tree_type == "Item" and self.data:
			item_codes = [r["entity"] for r in self.data if "entity" in r]

			item_group_map = frappe._dict(
				frappe.get_all(
					"Item",
					filters={"name": ["in", item_codes]},
					fields=["name", "item_group"],
					as_list=1,
				)
			)

			default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
			stock_data = frappe.get_all(
				"Bin",
				fields=["item_code", "actual_qty"],
				filters={"item_code": ["in", item_codes], "warehouse": default_warehouse},
			)
			stock_map = {d["item_code"]: d["actual_qty"] for d in stock_data}

			for r in self.data:
				item_code = r.get("entity")
				r["item_group"] = item_group_map.get(item_code)
				r["stock_in_hand"] = stock_map.get(item_code, 0.0)
