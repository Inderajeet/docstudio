from io import BytesIO

import frappe
from docx import Document
from frappe.tests.utils import FrappeTestCase

from docstudio.engine.access import SAVE_TO_FORM
from docstudio.engine.builtin import BUILTINS, is_applicable, layouts
from docstudio.engine.context import BuildContext
from docstudio.engine.highlights import resolve
from docstudio.engine.registry import build_model
from docstudio.export.docx_writer import build_docx
from docstudio.install import sync_templates
from docstudio.tests.utils import TEST_DT, make_record


def section(model, sid):
	return next((s for s in model["sections"] if s["id"] == sid), None)


class TestBuiltinTemplates(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		sync_templates()

	def test_sync_only_creates_applicable_templates(self):
		for entry in BUILTINS.values():
			exists = bool(frappe.db.exists("DocStudio Template", entry["template_name"]))
			self.assertEqual(exists, is_applicable(entry), entry["template_name"])
		for name in frappe.get_all("DocStudio Template", filters={"is_standard": 1}, pluck="name"):
			tpl = frappe.get_doc("DocStudio Template", name)
			self.assertEqual(tpl.template_type, "Built-in")
			self.assertTrue(tpl.field_mapping)

	def test_sync_keeps_user_remapping(self):
		entry = next((e for e in BUILTINS.values() if is_applicable(e)), None)
		if not entry:
			self.skipTest("No built-in DocType on this site")
		tpl = frappe.get_doc("DocStudio Template", entry["template_name"])
		row = next(r for r in tpl.field_mapping if r.slot == "item_description")
		row.fieldname = "description"
		tpl.save()
		sync_templates()
		tpl.reload()
		self.assertEqual(
			next(r for r in tpl.field_mapping if r.slot == "item_description").fieldname, "description"
		)
		row = next(r for r in tpl.field_mapping if r.slot == "item_description")
		row.fieldname = ""
		tpl.save()

	def test_invalid_mapping_rejected(self):
		entry = next((e for e in BUILTINS.values() if is_applicable(e)), None)
		if not entry:
			self.skipTest("No built-in DocType on this site")
		tpl = frappe.get_doc("DocStudio Template", entry["template_name"])
		next(r for r in tpl.field_mapping if r.slot == "item_rate").fieldname = "no_such_column"
		self.assertRaises(frappe.ValidationError, tpl.save)

	def test_quotation_layout(self):
		entry = BUILTINS["quotation"]
		if not is_applicable(entry):
			self.skipTest("Quotation not installed")
		company = frappe.get_all("Company", pluck="name", limit=1)
		doc = frappe.get_doc(
			{
				"doctype": "Quotation",
				"company": company[0] if company else None,
				"customer_name": "Bharat Builders",
				"transaction_date": "2026-09-01",
				"valid_till": "2026-09-30",
				"currency": "INR",
				"net_total": 1000,
				"grand_total": 1180,
				"rounded_total": 1180,
				"in_words": "INR One Thousand One Hundred And Eighty Only.",
				"terms": "<p>Prices are valid for 30 days.</p>",
				"items": [{"item_name": "Cement", "qty": 10, "uom": "Bag", "rate": 100, "amount": 1000}],
				"taxes": [
					{"charge_type": "On Net Total", "description": "CGST 9%", "tax_amount": 90},
					{"charge_type": "On Net Total", "description": "SGST 9%", "tax_amount": 90},
				],
			}
		)
		doc.name = "QTN-DS-TEST"
		for i, row in enumerate(doc.items + doc.taxes):
			row.name = f"row-{i}"
		tpl = frappe.get_doc("DocStudio Template", entry["template_name"])
		model = build_model(doc, template=tpl, preview=False)
		self.assertEqual(section(model, "s:title")["heading"]["display"], "QUOTATION")
		header = section(model, "s:header")
		self.assertEqual(header["left"]["title"], "Quotation To")
		self.assertEqual(header["left"]["items"][0]["display"], "Bharat Builders")
		items = section(model, "s:items")
		self.assertEqual(
			[c["label"] for c in items["columns"]], ["Description", "Qty", "Unit", "Rate", "Amount"]
		)
		totals = section(model, "s:totals")
		self.assertEqual(
			[n["label"] for n in totals["items"]], ["Net Total", "CGST 9%", "SGST 9%", "Grand Total"]
		)
		self.assertTrue(totals["items"][-1]["grand"])
		self.assertIsNotNone(section(model, "s:terms"))
		text = "\n".join(p.text for p in Document(BytesIO(build_docx(model))).paragraphs)
		self.assertIn("QUOTATION", text)
		self.assertIn("Prices are valid for 30 days.", text)

	def test_letter_layout_with_remapped_slots(self):
		"""Job Offer layout driven entirely by Field Mapping onto an unrelated DocType."""
		doc = frappe.get_doc(TEST_DT, make_record().name)
		mapping = {
			"company": "company",
			"applicant": "customer_name",
			"date": "posting_date",
			"designation": "site_name",
			"offer_terms_table": "items",
			"term_label": "item_name",
			"term_value": "qty",
			"terms": "notes",
			"applicant_email": "",
		}
		tpl = frappe._dict(
			name=None,
			template_type="Built-in",
			builtin_key="job_offer",
			theme=None,
			layout_json=None,
			default_terms=None,
			field_mapping=[frappe._dict(slot=k, fieldname=v) for k, v in mapping.items()],
		)
		ctx = BuildContext(doc, template=tpl, save_mode=SAVE_TO_FORM)
		ctx.highlights = resolve(doc.meta, None)
		sections = {s["id"]: s for s in layouts.job_offer(ctx)}
		self.assertEqual(sections["s:subject"]["node"]["display"], "Offer of Employment: Velachery")
		self.assertIn("Bharat Builders", sections["s:body"]["node"]["display"])
		self.assertTrue(sections["s:body"]["node"]["editable"])
		self.assertEqual(len(sections["s:offer_terms"]["rows"]), 2)
		self.assertIn("s:signature", sections)
		self.assertIn("Deliver", sections["s:terms"]["node"]["display"])


class TestTermsBlocks(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.doc = make_record()
		for title, doctypes in (("DS Electrical Terms", [TEST_DT]), ("DS Other Terms", ["ToDo"])):
			if not frappe.db.exists("DocStudio Terms Block", title):
				frappe.get_doc(
					{
						"doctype": "DocStudio Terms Block",
						"title": title,
						"content": f"<p>{title}: wiring as per IS 732.</p>",
						"applicable_doctypes": [{"document_type": d} for d in doctypes],
					}
				).insert()

	def model(self, patch=None, template=None):
		return build_model(frappe.get_doc(TEST_DT, self.doc.name), template=template, patch=patch)

	def test_chosen_block_is_inserted_before_signature(self):
		model = self.model({"layout": {"terms_block": "DS Electrical Terms"}})
		ids = [s["id"] for s in model["sections"]]
		self.assertEqual(ids[-2:], ["s:terms_block", "s:signature"])
		node = section(model, "s:terms_block")["node"]
		self.assertIn("IS 732", node["display"])
		self.assertTrue(node["editable"])

	def test_block_edits_and_scope(self):
		model = self.model(
			{
				"layout": {"terms_block": "DS Electrical Terms"},
				"overrides": {"terms:block": "<p>Edited clause</p>"},
			}
		)
		self.assertEqual(section(model, "s:terms_block")["node"]["display"], "<p>Edited clause</p>")
		# A block scoped to another DocType is never inserted.
		self.assertIsNone(section(self.model({"layout": {"terms_block": "DS Other Terms"}}), "s:terms_block"))

	def test_template_default_and_explicit_none(self):
		tpl = frappe._dict(
			name=None, template_type="Auto", theme=None, layout_json=None, default_terms="DS Electrical Terms"
		)
		self.assertIsNotNone(section(self.model(template=tpl), "s:terms_block"))
		self.assertIsNone(section(self.model({"layout": {"terms_block": ""}}, template=tpl), "s:terms_block"))
