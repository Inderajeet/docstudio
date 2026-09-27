from io import BytesIO

import frappe
from docx import Document
from frappe.tests.utils import FrappeTestCase

from docstudio.engine.registry import build_model
from docstudio.export.docx_writer import build_docx
from docstudio.tests.utils import TEST_DT, make_record


class TestTableAndColumnStyles(FrappeTestCase):
	def setUp(self):
		self.doc = make_record()

	def model(self, styles):
		return build_model(frappe.get_doc(TEST_DT, self.doc.name), patch={"styles": styles}, preview=False)

	def items(self, model):
		return next(s for s in model["sections"] if s["type"] == "table")

	def test_column_style_applies_to_cells_cell_wins(self):
		first_row = self.doc.items[0].name
		model = self.model(
			{
				"col:s:tbl:items:amount": {"bold": True, "color": "#AA0000"},
				f"c:items:{first_row}:amount": {"color": "#00AA00"},
			}
		)
		table = self.items(model)
		amount = [c["field"] for c in table["columns"]].index("amount")
		self.assertEqual(table["rows"][0]["cells"][amount]["style"], {"bold": True, "color": "#00AA00"})
		self.assertEqual(table["rows"][1]["cells"][amount]["style"], {"bold": True, "color": "#AA0000"})

	def test_table_style_override(self):
		model = self.model({"s:tbl:items": {"table_style": "Minimal", "header_fill": "#0F766E"}})
		self.assertEqual(self.items(model)["table_style"], {"table_style": "Minimal"})
		wdoc = Document(BytesIO(build_docx(model)))
		items = next(t for t in wdoc.tables if t.rows[0].cells[0].text == "S.No")
		# Minimal: no header shading, a rule under the header instead.
		self.assertIsNone(items.rows[0].cells[1]._tc.tcPr.find(
			"{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd"
		))

	def test_unknown_table_style_ignored(self):
		model = self.model({"s:tbl:items": {"table_style": "Fancy"}})
		self.assertNotIn("table_style", self.items(model))
