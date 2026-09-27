# Copyright (c) 2026, Inderajeet and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DocStudioTheme(Document):
	def validate(self):
		if self.is_standard and not self.flags.docstudio_sync and not self.is_new():
			frappe.throw(_("Standard themes cannot be edited. Duplicate this theme to customise it."))
		if (self.base_font_size or 0) < 6 or (self.heading_font_size or 0) < 6:
			frappe.throw(_("Font sizes must be at least 6 pt."))
		for fieldname in ("margin_top", "margin_bottom", "margin_left", "margin_right"):
			if not 0 <= (self.get(fieldname) or 0) <= 60:
				frappe.throw(_("{0} must be between 0 and 60 mm.").format(_(self.meta.get_label(fieldname))))

	def on_trash(self):
		if self.is_standard and not frappe.flags.in_uninstall:
			frappe.throw(_("Standard themes cannot be deleted."))

	def before_insert(self):
		# A duplicated standard theme becomes a regular, editable theme.
		if not self.flags.docstudio_sync:
			self.is_standard = 0
