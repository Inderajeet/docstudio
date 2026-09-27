"""Install/migrate hooks and the "Sync Standard Templates" action."""

import json
import os

import frappe
from frappe import _


def after_install():
	sync_standard()


def after_migrate():
	sync_standard()


def _load(filename):
	with open(os.path.join(os.path.dirname(__file__), "standard", filename)) as f:
		return json.load(f)


def sync_themes():
	for data in _load("themes.json"):
		name = data["theme_name"]
		doc = (
			frappe.get_doc("DocStudio Theme", name)
			if frappe.db.exists("DocStudio Theme", name)
			else frappe.new_doc("DocStudio Theme")
		)
		doc.update(data)
		doc.is_standard = 1
		doc.flags.docstudio_sync = True
		doc.save(ignore_permissions=True)


def sync_templates():
	"""Create/update built-in templates for DocTypes that exist on this site. Returns names synced."""
	from docstudio.engine.builtin import BUILTINS, is_applicable

	synced = []
	for key, entry in BUILTINS.items():
		doctype = entry["doctype"]
		if not is_applicable(entry):
			# Missing DocType, or a same-named custom DocType with a different shape.
			continue
		name = entry["template_name"]
		exists = frappe.db.exists("DocStudio Template", name)
		doc = frappe.get_doc("DocStudio Template", name) if exists else frappe.new_doc("DocStudio Template")
		doc.update(
			{
				"template_name": name,
				"reference_doctype": doctype,
				"template_type": "Built-in",
				"builtin_key": key,
				"is_standard": 1,
			}
		)
		if not exists:
			doc.enabled = 1
			doc.theme = entry.get("theme")
			doc.is_default = (
				0
				if frappe.db.exists("DocStudio Template", {"reference_doctype": doctype, "is_default": 1})
				else 1
			)
		# Keep user remappings: only add slots that are missing.
		existing_slots = {row.slot for row in doc.field_mapping}
		for slot, (fieldname, description) in entry.get("slots", {}).items():
			if slot not in existing_slots:
				doc.append(
					"field_mapping", {"slot": slot, "fieldname": fieldname, "description": description}
				)
		doc.flags.docstudio_sync = True
		doc.save(ignore_permissions=True)
		synced.append(name)
	return synced


def sync_standard():
	if not frappe.db.table_exists("DocStudio Theme"):
		return []
	sync_themes()
	settings = frappe.get_single("DocStudio Settings")
	if not settings.default_theme:
		settings.default_theme = "Business"
		settings.save(ignore_permissions=True)
	synced = sync_templates()
	frappe.db.commit()
	return synced


@frappe.whitelist(methods=["POST"])
def sync_standard_templates():
	frappe.only_for("System Manager")
	synced = sync_standard()
	return {"themes": len(_load("themes.json")), "templates": synced}
