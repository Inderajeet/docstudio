"""Whitelisted endpoints used by the preview. Every method checks permissions explicitly."""

import frappe
from frappe import _

from docstudio.engine import patch as patch_mod
from docstudio.engine.access import (
	DOCUMENT_ONLY,
	SAVE_TO_FORM,
	can_write,
	check_access,
	get_settings,
	resolve_save_mode,
)
from docstudio.engine.files import docx_filename, save_file
from docstudio.engine.registry import build_model, get_template, list_templates
from docstudio.engine.terms import applicable_blocks
from docstudio.engine.versions import latest_version, save_version
from docstudio.export.docx_writer import build_docx


def _theme_names():
	return frappe.get_all("DocStudio Theme", fields=["name"], order_by="is_standard desc, name asc")


def _parse_patch(patch):
	patch = patch_mod.normalize(patch)
	patch_mod.validate_patch_size(patch)
	return patch


@frappe.whitelist()
def get_preview(doctype, name, template=None, theme=None, save_mode=None, use_version=1):
	"""Initial load: model plus the edits of the latest saved document version (if any)."""
	doc = check_access(doctype, name)
	version = latest_version(doctype, name) if frappe.utils.cint(use_version) else None
	base_patch = version["patch"] if version else patch_mod.normalize(None)
	tpl = get_template(doctype, template or None)
	# Opening a document shows the DocType's current default layout (e.g. after an admin changed it);
	# the saved edits still apply. The saved theme is only reused with the template it was made for.
	if (
		version
		and not theme
		and version.get("theme")
		and version.get("template") == (tpl.name if tpl else None)
	):
		theme = version.get("theme")
	model = build_model(doc, tpl, theme or None, save_mode, base_patch)
	return {
		"model": model,
		"patch": base_patch,
		"version": {k: version[k] for k in ("name", "version_no", "creation", "owner")} if version else None,
		"templates": list_templates(doctype),
		"terms_blocks": applicable_blocks(doctype),
		"themes": _theme_names(),
		"can_write": can_write(doc),
		"is_admin": "System Manager" in frappe.get_roles(),
	}


@frappe.whitelist(methods=["POST"])
def render(doctype, name, template=None, theme=None, save_mode=None, patch=None):
	"""Rebuild the model with the current edits (totals and formatting come from the server)."""
	doc = check_access(doctype, name)
	return {
		"model": build_model(
			doc, get_template(doctype, template or None), theme or None, save_mode, _parse_patch(patch)
		)
	}


@frappe.whitelist(methods=["POST"])
def save(doctype, name, patch, template=None, theme=None, save_mode=None, modified=None):
	"""The preview's single Save button."""
	doc = check_access(doctype, name)
	patch = _parse_patch(patch)
	mode = resolve_save_mode(doc, save_mode)
	tpl = get_template(doctype, template or None)
	version = None

	if mode == SAVE_TO_FORM:
		if patch_mod.has_record_changes(patch):
			doc.check_permission("write")
			if modified and str(doc.modified) != str(modified):
				frappe.throw(
					_(
						"{0} {1} was changed by someone else after you opened the preview. Go back to the form and reload."
					).format(_(doctype), name),
					frappe.TimestampMismatchError,
				)
			patch_mod.apply_to_doc(doc, patch, strict=True)
			doc.save()
		rest = patch_mod.residual(patch)
		if not patch_mod.is_empty_patch(rest) or latest_version(doctype, name):
			fresh = frappe.get_doc(doctype, name)
			docx = build_docx(build_model(fresh, tpl, theme, mode, rest, preview=False))
			version = save_version(fresh, rest, tpl.name if tpl else None, theme, docx)
	else:
		docx = build_docx(
			build_model(frappe.get_doc(doctype, name), tpl, theme, DOCUMENT_ONLY, patch, preview=False)
		)
		version = save_version(doc, patch, tpl.name if tpl else None, theme, docx)

	doc.reload()
	return {
		"mode": mode,
		"modified": str(doc.modified),
		"version": {"name": version.name, "version_no": version.version_no} if version else None,
	}


def _docx_for(doctype, name, template, theme, save_mode, patch):
	doc = check_access(doctype, name)
	model = build_model(
		doc,
		get_template(doctype, template or None),
		theme or None,
		save_mode,
		_parse_patch(patch),
		preview=False,
	)
	return doc, build_docx(model)


@frappe.whitelist(methods=["POST"])
def download_docx(doctype, name, template=None, theme=None, save_mode=None, patch=None):
	"""Stream the .docx (called through open_url_post so the browser downloads it)."""
	doc, content = _docx_for(doctype, name, template, theme, save_mode, patch)
	fname = docx_filename(doctype, name)
	if get_settings().attach_on_download and frappe.has_permission(doctype, "write", doc=doc):
		save_file(fname, content, doctype, name)
	frappe.local.response.filename = fname
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"


@frappe.whitelist(methods=["POST"])
def attach_docx(doctype, name, template=None, theme=None, save_mode=None, patch=None):
	"""Generate the .docx and attach it to the record; returns the file URL."""
	doc, content = _docx_for(doctype, name, template, theme, save_mode, patch)
	if not frappe.has_permission(doctype, "write", doc=doc):
		frappe.throw(_("You need write permission to attach files to this record."), frappe.PermissionError)
	return save_file(docx_filename(doctype, name), content, doctype, name).file_url


def template_for_update(doctype, template=None):
	"""The template an admin action writes to; with none (Auto layout) an Auto template is
	created and made the default so the change applies to future documents."""
	frappe.only_for("System Manager")
	from docstudio.engine.access import is_doctype_supported

	if not is_doctype_supported(doctype):
		frappe.throw(_("DocStudio is not available for {0}.").format(_(doctype)))
	if template:
		tpl = frappe.get_doc("DocStudio Template", template)
		if tpl.reference_doctype != doctype:
			frappe.throw(_("Template {0} is not for {1}.").format(template, _(doctype)))
		return tpl
	name = _("{0} (Auto)").format(_(doctype))
	if frappe.db.exists("DocStudio Template", name):
		return frappe.get_doc("DocStudio Template", name)
	return frappe.get_doc(
		{
			"doctype": "DocStudio Template",
			"template_name": name,
			"reference_doctype": doctype,
			"template_type": "Auto",
			"is_default": 0
			if frappe.db.exists("DocStudio Template", {"reference_doctype": doctype, "is_default": 1})
			else 1,
			"enabled": 1,
		}
	)


@frappe.whitelist(methods=["POST"])
def save_layout_to_template(doctype, layout, template=None):
	"""Admin only: make the current section order/visibility the template's layout."""
	tpl = template_for_update(doctype, template)
	layout = patch_mod.clean_layout(frappe.parse_json(layout) or {})
	tpl.layout_json = frappe.as_json(layout) if layout else None
	tpl.save()
	return tpl.name
