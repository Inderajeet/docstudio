"""Saving generated .docx files as Frappe File records."""

import os
import re

import frappe
from frappe.utils import get_files_path


def docx_filename(doctype, name):
	return re.sub(r"[\\/:*?\"<>|\s]+", "-", f"{doctype}-{name}").strip("-") + ".docx"


def save_file(fname, content, attached_to_doctype, attached_to_name, is_private=1):
	"""Save ``content`` under exactly ``fname`` attached to a record, replacing an older copy.

	Inserting a File with ``content`` (rather than frappe.utils.file_manager.save_file) writes
	the file once, so Frappe doesn't append a hash suffix to the file name.
	"""
	for old in frappe.get_all(
		"File",
		filters={
			"file_name": fname,
			"attached_to_doctype": attached_to_doctype,
			"attached_to_name": attached_to_name,
		},
		pluck="name",
	):
		frappe.delete_doc("File", old, ignore_permissions=True, delete_permanently=True)
	stale = get_files_path(fname, is_private=is_private)
	if os.path.exists(stale) and not frappe.db.exists("File", {"file_url": ("like", f"%/{fname}")}):
		os.remove(stale)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"attached_to_doctype": attached_to_doctype,
			"attached_to_name": attached_to_name,
			"is_private": is_private,
			"content": content,
		}
	)
	file_doc.insert(ignore_permissions=True)
	return file_doc
