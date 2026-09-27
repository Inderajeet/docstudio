"""Who may use DocStudio, on which DocTypes, and in which save mode."""

import frappe
from frappe import _

SAVE_TO_FORM = "Save to Form"
DOCUMENT_ONLY = "Save as Document Only"

# DocStudio's own DocTypes never get a preview button.
OWN_MODULE = "DocStudio"


def get_settings():
	return frappe.get_cached_doc("DocStudio Settings")


def user_is_allowed(user=None):
	settings = get_settings()
	if not settings.enabled:
		return False
	roles = {r.role for r in settings.allowed_roles}
	if not roles:
		return True
	user_roles = set(frappe.get_roles(user))
	return bool(user_roles & (roles | {"System Manager"}))


def excluded_doctypes():
	return {r.document_type for r in get_settings().excluded_doctypes}


def is_doctype_supported(doctype):
	if not doctype or not frappe.db.exists("DocType", doctype):
		return False
	meta = frappe.get_meta(doctype)
	if meta.istable or meta.issingle or meta.get("is_virtual") or meta.module == OWN_MODULE:
		return False
	return doctype not in excluded_doctypes()


def check_access(doctype, name, ptype="read"):
	"""Load the record after checking every DocStudio and Frappe permission rule."""
	if not user_is_allowed():
		frappe.throw(_("You are not allowed to use DocStudio."), frappe.PermissionError)
	if not is_doctype_supported(doctype):
		frappe.throw(_("DocStudio is not available for {0}.").format(_(doctype)), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission(ptype)
	return doc


def can_write(doc):
	return doc.docstatus == 0 and bool(frappe.has_permission(doc.doctype, "write", doc=doc))


def resolve_save_mode(doc, requested=None):
	"""Submitted/cancelled records and read-only users always get document-only saves."""
	if not can_write(doc):
		return DOCUMENT_ONLY
	if requested in (SAVE_TO_FORM, DOCUMENT_ONLY):
		return requested
	return get_settings().default_save_mode or SAVE_TO_FORM


def boot_session(bootinfo):
	if frappe.session.user == "Guest":
		return
	try:
		settings = get_settings()
	except Exception:
		# e.g. during install before the Single has been created
		return
	bootinfo.docstudio = {
		"enabled": bool(settings.enabled),
		"allowed": user_is_allowed(),
		"excluded": sorted(excluded_doctypes()),
	}
