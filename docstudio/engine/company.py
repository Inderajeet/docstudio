"""Letterhead and signature data from the record linked by the company field.

Works for ERPNext's Company as well as any custom "company-like" DocType: fields are
looked up by common names and only used when they exist on that DocType.
"""

import re

import frappe
from frappe import _
from frappe.utils import cstr, strip_html

NAME_FIELDS = ("company_name", "organization_name", "title")
PHONE_FIELDS = ("phone_no", "phone", "mobile_no", "contact_phone")
EMAIL_FIELDS = ("email", "email_id", "contact_email")
WEBSITE_FIELDS = ("website",)
TAX_FIELDS = ("tax_id", "gstin", "gst_number", "vat_id")
LOGO_FIELDS = ("company_logo", "logo", "image")


def html_to_text(value):
	text = re.sub(r"<br\s*/?>", "\n", cstr(value), flags=re.IGNORECASE)
	text = re.sub(r"</(p|div)>", "\n", text, flags=re.IGNORECASE)
	lines = [ln.strip().rstrip(",") for ln in strip_html(text).split("\n")]
	return "\n".join(ln for ln in lines if ln)


def _pick(rec, names):
	for n in names:
		if rec.meta.has_field(n) and rec.get(n):
			return n, rec.get(n)
	return None, None


def _linked_address(linked_dt, name):
	if not frappe.db.exists("DocType", "Address"):
		return ""
	address_meta = frappe.get_meta("Address")
	order = [
		f"{flag} desc"
		for flag in ("is_your_company_address", "is_primary_address")
		if address_meta.has_field(flag)
	]
	rows = frappe.get_all(
		"Address",
		filters=[["Dynamic Link", "link_doctype", "=", linked_dt], ["Dynamic Link", "link_name", "=", name]],
		pluck="name",
		order_by=", ".join(order) or "creation asc",
		limit=1,
	)
	if not rows:
		return ""
	from frappe.contacts.doctype.address.address import get_address_display

	return html_to_text(get_address_display(rows[0]))


def _letter_head_image(doc, rec):
	name = doc.get("letter_head") or (
		rec.get("default_letter_head") if rec.meta.has_field("default_letter_head") else None
	)
	if not name:
		name = frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0}, "name")
	if name and frappe.db.exists("Letter Head", name):
		return frappe.db.get_value("Letter Head", name, "image")
	return None


def get_company_info(doc, company_field):
	"""Dict with display name, contact lines and logo URL, or None."""
	if not company_field:
		return None
	df = doc.meta.get_field(company_field)
	value = doc.get(company_field)
	if not df or not value:
		return None
	if df.fieldtype != "Link":
		return {"name": cstr(value), "lines": [], "logo": None, "tax_line": None}
	linked_dt = df.options
	if not frappe.db.exists(linked_dt, value):
		return None
	rec = frappe.get_cached_doc(linked_dt, value)

	_f, display_name = _pick(rec, NAME_FIELDS)
	address = html_to_text(doc.get("company_address_display")) if doc.get("company_address_display") else ""
	if not address:
		_f, addr_field = _pick(rec, ("address", "registered_address", "custom_registered_address"))
		address = html_to_text(addr_field) if addr_field else _linked_address(linked_dt, value)

	lines = []
	if address:
		lines.append(address)
	contact = []
	_f, phone = _pick(rec, PHONE_FIELDS)
	_f, email = _pick(rec, EMAIL_FIELDS)
	_f, website = _pick(rec, WEBSITE_FIELDS)
	if phone:
		contact.append(_("Phone: {0}").format(phone))
	if email:
		contact.append(_("Email: {0}").format(email))
	if website:
		contact.append(cstr(website))
	if contact:
		lines.append("  |  ".join(contact))

	tax_line = None
	if doc.get("company_gstin"):
		tax_line = _("GSTIN: {0}").format(doc.get("company_gstin"))
	else:
		tax_field, tax = _pick(rec, TAX_FIELDS)
		if tax:
			tax_line = f"{_(rec.meta.get_label(tax_field))}: {tax}"
	if tax_line:
		lines.append(tax_line)

	_f, logo = _pick(rec, LOGO_FIELDS)
	if not logo:
		logo = _letter_head_image(doc, rec)

	return {"name": cstr(display_name or value), "lines": lines, "logo": logo or None}
