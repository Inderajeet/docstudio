import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate

from docstudio.engine import model as m
from docstudio.engine.access import DOCUMENT_ONLY, SAVE_TO_FORM
from docstudio.engine.registry import build_model
from docstudio.tests.utils import TEST_DT, make_record


def all_nodes(model):
	return list(m.iter_nodes(model))


def section(model, section_type, label=None):
	for s in model["sections"]:
		if s["type"] == section_type and (label is None or s.get("label") == label):
			return s
	return None


class TestAutoLayout(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.doc = make_record()

	def model(self, **kw):
		return build_model(frappe.get_doc(TEST_DT, self.doc.name), **kw)

	def test_section_order(self):
		types = [s["type"] for s in self.model()["sections"]]
		self.assertEqual(types[:3], ["letterhead", "title", "header"])
		self.assertEqual(types[-1], "signature")
		self.assertEqual(types[types.index("table") + 1], "totals")

	def test_letterhead_and_signature_from_company_link(self):
		model = self.model()
		lh = section(model, "letterhead")
		self.assertEqual(lh["company"]["name"]["display"], "Acme Test Traders")
		lines = "\n".join(n["display"] for n in lh["company"]["lines"])
		self.assertIn("Chennai 600002", lines)
		self.assertIn("sales@acme.test", lines)
		self.assertIn("33ABCDE1234F1Z5", lines)
		sig = section(model, "signature")
		self.assertEqual(sig["lines"][0]["display"], "For Acme Test Traders")

	def test_title_and_header(self):
		model = self.model()
		self.assertEqual(section(model, "title")["heading"]["display"], TEST_DT.upper())
		header = section(model, "header")
		self.assertEqual(header["left"]["items"][0]["display"], "Bharat Builders")
		right = {n["id"]: n for n in header["right"]["items"]}
		self.assertEqual(right["hdr:number"]["display"], self.doc.name)
		self.assertEqual(right["f:posting_date"]["display"], formatdate("2026-09-01"))

	def test_skipped_fields(self):
		ids = {n["id"] for n in all_nodes(self.model())}
		for fieldname in (
			"internal_ref",
			"print_hidden_ref",
			"unused_field",
			"currency",
			"naming_series",
			"owner",
		):
			self.assertNotIn(m.field_id(fieldname), ids)
		# Fields shown in letterhead/header are not repeated in the body.
		body = [
			n["id"]
			for s in self.model()["sections"]
			if s["type"] == "fields"
			for c in s["columns"]
			for n in c
		]
		self.assertNotIn("f:customer_name", body)
		self.assertNotIn("f:company", body)

	def test_empty_section_dropped_and_column_break_boxed(self):
		model = self.model()
		self.assertIsNone(section(model, "fields", "Nothing Here"))
		details = section(model, "fields", "Details")
		self.assertEqual(len(details["columns"]), 2)
		self.assertTrue(details["boxed"])
		self.assertEqual([n["id"] for n in details["columns"][1]], ["f:site_name", "f:is_urgent"])
		self.assertEqual(details["columns"][1][1]["display"], "Yes")

	def test_table_columns(self):
		table = section(self.model(preview=False), "table")
		self.assertEqual([c["field"] for c in table["columns"]], ["item_name", "qty", "rate", "amount"])
		self.assertEqual(table["columns"][2]["align"], "right")
		self.assertEqual(len(table["rows"]), 2)

	def test_currency_formatting(self):
		table = section(self.model(), "table")
		rate = table["rows"][0]["cells"][2]["display"]
		self.assertIn("1,000.00", rate)
		self.assertIn("₹", rate)
		totals = section(self.model(), "totals")
		self.assertIn("4,371.00", totals["items"][0]["display"])

	def test_rich_text(self):
		rt = section(self.model(), "rich_text")
		self.assertEqual(rt["label"], "Notes")
		self.assertIn("<strong>before</strong>", rt["node"]["display"])
		self.assertTrue(rt["node"]["html"])

	def test_editability_by_mode(self):
		nodes = {n["id"]: n for n in all_nodes(self.model(save_mode=SAVE_TO_FORM))}
		self.assertTrue(nodes["f:reference_no"]["writable"])
		self.assertFalse(nodes["f:grand_total"]["editable"])  # read-only field
		self.assertFalse(nodes["lh:name"]["editable"])  # letterhead is not the record's data

		nodes = {n["id"]: n for n in all_nodes(self.model(save_mode=DOCUMENT_ONLY))}
		self.assertTrue(nodes["lh:name"]["editable"])
		self.assertFalse(nodes["lh:name"]["writable"])
		self.assertTrue(nodes["f:grand_total"]["editable"])

		export = all_nodes(self.model(preview=False))
		self.assertFalse(any(n["editable"] for n in export))

	def test_template_highlight_override(self):
		tpl = frappe._dict(
			name=None,
			template_type="Auto",
			theme=None,
			layout_json=None,
			default_terms=None,
			party_field="site_name",
			date_field=None,
			title_field=None,
			total_field=None,
			company_field=None,
		)
		model = build_model(frappe.get_doc(TEST_DT, self.doc.name), template=tpl)
		self.assertEqual(section(model, "header")["left"]["items"][0]["display"], "Velachery")
