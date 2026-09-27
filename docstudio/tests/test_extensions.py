from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from docstudio.engine import auto_layout
from docstudio.engine import model as m
from docstudio.engine.registry import build_model
from docstudio.tests.utils import TEST_DT, make_record

HOOK_ENTRY = {
	"key": "test_custom",
	"label": "Test Custom Layout",
	"doctype": TEST_DT,
	"builder": "docstudio.tests.test_extensions.custom_builder",
}


def custom_builder(ctx):
	"""A layout from another app: the auto layout plus a custom banner section."""
	sections = auto_layout.build_sections(ctx)
	banner = ctx.text("custom:banner", "Thank you for your business!", style={"italic": True})
	sections.insert(-1, m.section("s:custom_banner", "text", node=banner))
	return sections


class TestCustomTemplateHook(FrappeTestCase):
	def test_custom_layout_via_hook(self):
		doc = make_record()
		with patch("docstudio.engine.registry.custom_templates", return_value={"test_custom": HOOK_ENTRY}):
			tpl = frappe.get_doc(
				{
					"doctype": "DocStudio Template",
					"template_name": "Test Custom",
					"reference_doctype": TEST_DT,
					"template_type": "Custom",
					"custom_builder": "test_custom",
				}
			).insert()
			model = build_model(frappe.get_doc(TEST_DT, doc.name), template=tpl, preview=False)
		ids = [s["id"] for s in model["sections"]]
		self.assertEqual(ids[-2:], ["s:custom_banner", "s:signature"])

	def test_unregistered_custom_layout_rejected(self):
		make_record()
		tpl = frappe.get_doc(
			{
				"doctype": "DocStudio Template",
				"template_name": "Test Missing Custom",
				"reference_doctype": TEST_DT,
				"template_type": "Custom",
				"custom_builder": "not_registered",
			}
		)
		self.assertRaises(frappe.ValidationError, tpl.insert)

