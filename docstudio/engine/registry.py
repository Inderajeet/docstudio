"""Template resolution and the single ``build_model`` entry point."""

import frappe
from frappe import _

from docstudio.engine import auto_layout
from docstudio.engine import patch as patch_mod
from docstudio.engine.access import resolve_save_mode
from docstudio.engine.context import BuildContext
from docstudio.engine.highlights import resolve as resolve_highlights
from docstudio.engine.terms import insert_terms_block
from docstudio.engine.theme import resolve_theme

MODEL_VERSION = 1


def custom_templates():
	"""All layouts registered through the docstudio_templates hook, keyed by ``key``."""
	out = {}
	for entry in frappe.get_hooks("docstudio_templates") or []:
		if isinstance(entry, dict) and entry.get("key") and entry.get("builder"):
			out[entry["key"]] = entry
	return out


def get_template(doctype, template_name=None):
	if template_name:
		tpl = frappe.get_cached_doc("DocStudio Template", template_name)
		if tpl.reference_doctype != doctype or not tpl.enabled:
			frappe.throw(_("Template {0} cannot be used for {1}.").format(template_name, _(doctype)))
		return tpl
	name = frappe.db.get_value(
		"DocStudio Template", {"reference_doctype": doctype, "is_default": 1, "enabled": 1}, "name"
	)
	return frappe.get_cached_doc("DocStudio Template", name) if name else None


def get_builder(template):
	if not template or template.template_type == "Auto":
		return auto_layout.build_sections
	if template.template_type == "Built-in":
		from docstudio.engine.builtin import BUILTINS

		entry = BUILTINS.get(template.builtin_key)
		if not entry:
			frappe.throw(_("Built-in layout {0} is not available.").format(template.builtin_key))
		return entry["builder"]
	if template.template_type != "Custom":
		# A type this version doesn't know (e.g. data from another edition): use the auto layout.
		return auto_layout.build_sections
	entry = custom_templates().get(template.custom_builder)
	if not entry:
		frappe.throw(_("Custom layout {0} is not installed on this site.").format(template.custom_builder))
	return frappe.get_attr(entry["builder"])


def list_templates(doctype):
	return frappe.get_all(
		"DocStudio Template",
		filters={"reference_doctype": doctype, "enabled": 1},
		fields=["name", "template_type", "is_default", "theme"],
		order_by="is_default desc, name asc",
	)


def build_model(doc, template=None, theme_name=None, save_mode=None, patch=None, preview=True):
	"""Build the DocModel for ``doc`` with the edits ``patch`` applied."""
	patch = patch_mod.normalize(patch)
	save_mode = resolve_save_mode(doc, save_mode)

	if patch_mod.has_record_changes(patch):
		patch_mod.apply_to_doc(doc, patch, strict=False)
		patch_mod.recalculate(doc, patch)

	theme = resolve_theme(theme_name, template)
	ctx = BuildContext(doc, template=template, theme=theme, save_mode=save_mode, preview=preview)
	ctx.highlights = resolve_highlights(doc.meta, template)

	sections = get_builder(template)(ctx)
	model = {
		"version": MODEL_VERSION,
		"meta": {
			"doctype": doc.doctype,
			"name": doc.name,
			"docstatus": doc.docstatus,
			"modified": str(doc.modified),
			"template": template.name if template else None,
			"template_type": template.template_type if template else "Auto",
			"theme": theme.get("name"),
			"save_mode": save_mode,
			"highlights": ctx.highlights,
			"default_terms": template.default_terms if template else None,
		},
		"theme": theme,
		"sections": sections,
	}
	insert_terms_block(model, ctx, template, patch)
	if template and template.layout_json:
		layout = frappe.parse_json(template.layout_json) or {}
		patch_mod.apply_layout(model, layout)
	for method in frappe.get_hooks("docstudio_model_processors") or []:
		frappe.get_attr(method)(ctx, model)
	return patch_mod.apply_to_model(model, patch)
