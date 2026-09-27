"""DocStudio Document Version: edits kept with the document instead of the record."""

import json

import frappe
from frappe.utils import cint

from docstudio.engine import patch as patch_mod
from docstudio.engine.files import docx_filename, save_file

VERSION_DOCTYPE = "DocStudio Document Version"


def latest_version(doctype, name):
	rows = frappe.get_all(
		VERSION_DOCTYPE,
		filters={"reference_doctype": doctype, "reference_name": name},
		fields=["name", "version_no", "template", "theme", "content", "creation", "owner"],
		order_by="version_no desc",
		limit=1,
	)
	if not rows:
		return None
	row = rows[0]
	row["patch"] = patch_mod.normalize(row.pop("content") or "{}")
	return row


def save_version(doc, patch, template=None, theme=None, docx_bytes=None):
	last = frappe.get_all(
		VERSION_DOCTYPE,
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="version_no",
		order_by="version_no desc",
		limit=1,
	)
	next_no = cint(last[0] if last else 0) + 1
	version = frappe.get_doc(
		{
			"doctype": VERSION_DOCTYPE,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"version_no": next_no,
			"template": template,
			"theme": theme,
			"content": json.dumps(patch),
		}
	)
	version.insert(ignore_permissions=True)
	if docx_bytes:
		fname = docx_filename(doc.doctype, f"{doc.name}-v{next_no}")
		file_doc = save_file(fname, docx_bytes, VERSION_DOCTYPE, version.name)
		version.db_set("docx_file", file_doc.file_url)
	return version
