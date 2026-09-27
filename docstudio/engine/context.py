"""BuildContext: everything a layout builder needs, including editability rules.

Custom template builders (see ``docstudio.engine.registry``) receive one of these, so they
never need to re-implement permission or formatting rules.
"""

import frappe

from docstudio.engine import model as m
from docstudio.engine.access import DOCUMENT_ONLY, SAVE_TO_FORM
from docstudio.engine.formatting import TYPED_EDITABLE


class BuildContext:
	def __init__(self, doc, template=None, theme=None, save_mode=SAVE_TO_FORM, preview=True):
		self.doc = doc
		self.meta = doc.meta
		self.template = template  # DocStudio Template doc or None
		self.theme = theme or {}
		self.save_mode = save_mode
		self.preview = preview  # False when building for export: nothing is editable
		self._write_levels = None

	# ── editability ──────────────────────────────────────────
	@property
	def document_only(self):
		return self.save_mode == DOCUMENT_ONLY

	def _writable_levels(self):
		if self._write_levels is None:
			self._write_levels = (
				set(self.doc.get_permlevel_access("write")) if self.doc.docstatus == 0 else set()
			)
		return self._write_levels

	def field_writable(self, df, row=None):
		"""True when the value may be written back to the record (Save to Form)."""
		if df.fieldtype not in TYPED_EDITABLE or df.read_only or df.hidden or df.get("is_virtual"):
			return False
		if df.fieldtype == "Read Only":
			return False
		if self.doc.docstatus != 0 or (df.permlevel or 0) not in self._writable_levels():
			return False
		if df.set_only_once and row is None and self.doc.get(df.fieldname):
			return False
		return True

	def field_flags(self, df, row=None):
		"""(editable, writable) for a value node in the current save mode."""
		if not self.preview:
			return False, False
		if self.document_only:
			# Any value can be changed in the document; typed values are kept typed so totals recalc.
			typed = df.fieldtype in TYPED_EDITABLE and df.fieldtype != "Read Only"
			return True, typed
		w = self.field_writable(df, row)
		return w, w

	@property
	def text_editable(self):
		"""Free text (headings, letterhead, signature) is only editable in document-only mode."""
		return self.preview and self.document_only

	def table_rows_editable(self, table_df):
		if not self.preview:
			return False
		if self.document_only:
			return True
		return self.field_writable(frappe._dict(table_df.as_dict(), fieldtype="Data"))

	# ── node helpers ─────────────────────────────────────────
	def field_node(self, fieldname, label=None):
		df = self.meta.get_field(fieldname)
		if not df:
			return None
		editable, writable = self.field_flags(df)
		return m.value_node(
			df, self.doc.get(fieldname), parent=self.doc, editable=editable, writable=writable, label=label
		)

	def cell_node(self, table_fieldname, row, df):
		editable, writable = self.field_flags(df, row)
		return m.value_node(
			df,
			row.get(df.fieldname),
			row=row,
			parent=self.doc,
			table=table_fieldname,
			editable=editable,
			writable=writable,
		)

	def text(self, node_id, display, html=False, style=None, label=None):
		return m.text_node(node_id, display, editable=self.text_editable, html=html, style=style, label=label)

	def mapped(self, slot, default=None):
		"""Fieldname mapped to a template slot (built-in templates), else ``default``."""
		if self.template:
			for row in self.template.get("field_mapping") or []:
				if row.slot == slot:
					return row.fieldname or None
		return default
