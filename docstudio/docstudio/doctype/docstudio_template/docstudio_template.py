# Copyright (c) 2026, Inderajeet and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from docstudio.engine.access import is_doctype_supported
from docstudio.engine.highlights import HIGHLIGHT_KEYS

LOCKED_STANDARD_FIELDS = ("reference_doctype", "template_type", "builtin_key", "template_name")


class DocStudioTemplate(Document):
	def validate(self):
		if not is_doctype_supported(self.reference_doctype):
			frappe.throw(_("DocStudio cannot be used with {0}.").format(_(self.reference_doctype)))
		self.validate_standard()
		self.validate_layout_source()
		self.validate_highlights()
		if self.layout_json:
			frappe.parse_json(self.layout_json)

	def validate_standard(self):
		if not self.is_standard or self.flags.docstudio_sync or self.is_new():
			return
		before = self.get_doc_before_save()
		for fieldname in LOCKED_STANDARD_FIELDS:
			if before and before.get(fieldname) != self.get(fieldname):
				frappe.throw(
					_("{0} of a standard template cannot be changed. Duplicate the template instead.").format(
						_(self.meta.get_label(fieldname))
					)
				)

	def validate_layout_source(self):
		if self.template_type == "Built-in":
			from docstudio.engine.builtin import BUILTINS

			if self.builtin_key not in BUILTINS:
				frappe.throw(
					_(
						"Built-in templates are created by DocStudio; use Sync Standard Templates in DocStudio Settings."
					)
				)
			self.validate_field_mapping(BUILTINS[self.builtin_key])
		elif self.template_type == "Custom":
			from docstudio.engine.registry import custom_templates

			if self.custom_builder not in custom_templates():
				frappe.throw(
					_(
						"Custom layout {0} is not registered by any installed app (docstudio_templates hook)."
					).format(frappe.bold(self.custom_builder))
				)
		else:
			self.builtin_key = None
			self.custom_builder = None

	def validate_field_mapping(self, entry):
		"""Every mapped fieldname must exist on the DocType (or on the slot's child table)."""
		from docstudio.engine.builtin import slot_scope

		meta = frappe.get_meta(self.reference_doctype)
		mapped = {row.slot: row.fieldname for row in self.field_mapping}
		for row in self.field_mapping:
			if row.slot not in entry["slots"]:
				frappe.throw(
					_("Row {0}: {1} is not a slot of this layout.").format(row.idx, frappe.bold(row.slot))
				)
			if not row.fieldname or row.fieldname == entry["slots"][row.slot][0]:
				# Shipped defaults may not exist on every site (e.g. HSN without India Compliance);
				# they are skipped at render time. Only user-entered fieldnames are checked.
				continue
			table_slot = slot_scope(entry, row.slot)
			target = meta
			if table_slot:
				table_field = mapped.get(table_slot) or entry["slots"][table_slot][0]
				table_df = meta.get_field(table_field)
				if not table_df or table_df.fieldtype != "Table":
					continue  # reported on the table slot's own row
				target = frappe.get_meta(table_df.options)
			if not target.has_field(row.fieldname):
				frappe.throw(
					_("Row {0}: {1} is not a field of {2}.").format(
						row.idx, frappe.bold(row.fieldname), _(target.name)
					)
				)

	def validate_highlights(self):
		meta = frappe.get_meta(self.reference_doctype)
		for key in HIGHLIGHT_KEYS:
			fieldname = self.get(key)
			if fieldname and not meta.has_field(fieldname):
				frappe.throw(
					_("{0}: {1} is not a field of {2}.").format(
						_(self.meta.get_label(key)), fieldname, _(self.reference_doctype)
					)
				)

	def on_update(self):
		if self.is_default:
			frappe.db.set_value(
				"DocStudio Template",
				{"reference_doctype": self.reference_doctype, "is_default": 1, "name": ("!=", self.name)},
				"is_default",
				0,
			)

	def before_insert(self):
		if not self.flags.docstudio_sync:
			self.is_standard = 0

	def on_trash(self):
		if self.is_standard and not frappe.flags.in_uninstall:
			frappe.throw(_("Standard templates cannot be deleted. Disable them instead."))


@frappe.whitelist()
def get_field_options(doctype):
	"""Fields offered in the Highlight Fields dropdowns."""
	frappe.has_permission("DocStudio Template", "read", throw=True)
	meta = frappe.get_meta(doctype)
	skip = {
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Table",
		"Table MultiSelect",
		"Fold",
		"Heading",
	}
	return [
		{"value": df.fieldname, "label": f"{_(df.label or df.fieldname)} ({df.fieldname})"}
		for df in meta.fields
		if df.fieldtype not in skip
	]
