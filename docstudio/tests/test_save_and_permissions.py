import json

import frappe
from frappe.tests.utils import FrappeTestCase

from docstudio import api
from docstudio.engine.access import DOCUMENT_ONLY, SAVE_TO_FORM
from docstudio.tests.utils import TEST_DT, make_record


class TestSaveAndPermissions(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.doc = make_record()

	def tearDown(self):
		frappe.set_user("Administrator")

	def save(self, patch, mode=SAVE_TO_FORM, **kw):
		return api.save(TEST_DT, self.doc.name, json.dumps(patch), save_mode=mode, **kw)

	def test_save_to_form_writes_fields_and_rows(self):
		first_row = self.doc.items[0].name
		second_row = self.doc.items[1].name
		self.save(
			{
				"fields": {"reference_no": "REF-NEW", "posting_date": "2026-09-05", "is_urgent": 0},
				"rows": {"items": {first_row: {"qty": 5}}},
				"deleted_rows": {"items": [second_row]},
				"added_rows": {"items": [{"name": "new-1", "item_name": "Steel", "qty": 2, "rate": 50}]},
			}
		)
		doc = frappe.get_doc(TEST_DT, self.doc.name)
		self.assertEqual(doc.reference_no, "REF-NEW")
		self.assertEqual(str(doc.posting_date), "2026-09-05")
		self.assertEqual(doc.is_urgent, 0)
		self.assertEqual([r.item_name for r in doc.items], ["Cement", "Steel"])
		self.assertEqual(doc.items[0].qty, 5)
		self.assertFalse(frappe.db.exists("DocStudio Document Version", {"reference_name": doc.name}))

	def test_read_only_and_unknown_fields_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			self.save({"fields": {"grand_total": 1}})
		with self.assertRaises(frappe.ValidationError):
			self.save({"fields": {"no_such_field": "x"}})
		with self.assertRaises(frappe.ValidationError):
			self.save({"fields": {"owner": "Guest"}})
		with self.assertRaises(frappe.ValidationError):
			self.save({"fields": {"priority": "Not An Option"}})

	def test_rich_text_is_sanitized(self):
		self.save({"fields": {"notes": '<p>ok</p><script>alert(1)</script><img src=x onerror="alert(2)">'}})
		notes = frappe.db.get_value(TEST_DT, self.doc.name, "notes")
		self.assertNotIn("<script", notes)
		self.assertNotIn("onerror", notes)

	def test_document_only_keeps_record_unchanged(self):
		res = self.save(
			{"fields": {"reference_no": "DOC-ONLY"}, "overrides": {"sig:title": "Director"}},
			mode=DOCUMENT_ONLY,
		)
		self.assertEqual(res["mode"], DOCUMENT_ONLY)
		self.assertEqual(frappe.db.get_value(TEST_DT, self.doc.name, "reference_no"), "REF-77")
		version = frappe.get_doc("DocStudio Document Version", res["version"]["name"])
		self.assertEqual(version.version_no, 1)
		self.assertTrue(version.docx_file)
		# Reopening the preview starts from the saved version.
		preview = api.get_preview(TEST_DT, self.doc.name)
		self.assertEqual(preview["patch"]["fields"]["reference_no"], "DOC-ONLY")
		nodes = {
			n["id"]: n
			for s in preview["model"]["sections"]
			if s["type"] == "fields"
			for c in s["columns"]
			for n in c
		}
		self.assertEqual(nodes["f:reference_no"]["display"], "DOC-ONLY")

	def test_stale_preview_rejected(self):
		with self.assertRaises(frappe.TimestampMismatchError):
			self.save({"fields": {"reference_no": "X"}}, modified="2000-01-01 00:00:00")

	def test_permissions(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			api.get_preview(TEST_DT, self.doc.name)
		with self.assertRaises(frappe.PermissionError):
			self.save({"fields": {"reference_no": "X"}})

	def test_allowed_roles_and_exclusions(self):
		settings = frappe.get_single("DocStudio Settings")
		try:
			settings.append("excluded_doctypes", {"document_type": TEST_DT})
			settings.save()
			with self.assertRaises(frappe.PermissionError):
				api.get_preview(TEST_DT, self.doc.name)
		finally:
			settings.reload()
			settings.excluded_doctypes = []
			settings.save()

	def test_render_recalculates_new_row_amount(self):
		patch = {"added_rows": {"items": [{"name": "new-x", "item_name": "Tiles", "qty": 4, "rate": 25}]}}
		model = api.render(TEST_DT, self.doc.name, patch=json.dumps(patch))["model"]
		table = next(s for s in model["sections"] if s["type"] == "table")
		new = next(r for r in table["rows"] if r["name"] == "new-x")
		self.assertIn("100.00", new["cells"][3]["display"])
