# Copyright (c) 2026, Inderajeet and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DocStudioSettings(Document):
	def on_update(self):
		# Boot info (button visibility, excluded DocTypes) is cached per session.
		frappe.clear_cache()
