"""Value formatting shared by every layout, so preview and .docx show identical text."""

import datetime
import re
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, fmt_money, get_datetime, get_time, getdate
from frappe.utils.formatters import format_value
from frappe.utils.html_utils import sanitize_html

NUMERIC = frozenset(("Currency", "Float", "Int", "Long Int", "Percent"))
RICH = frozenset(("Text Editor", "HTML Editor"))
MULTILINE = frozenset(("Small Text", "Text", "Long Text", "Markdown Editor"))

# Fieldtypes a user may type a new value for (in preview or when writing back).
TYPED_EDITABLE = frozenset(
	(
		"Data",
		"Small Text",
		"Text",
		"Long Text",
		"Text Editor",
		"Link",
		"Select",
		"Date",
		"Datetime",
		"Time",
		"Int",
		"Long Int",
		"Float",
		"Currency",
		"Percent",
		"Check",
		"Phone",
		"Autocomplete",
		"Read Only",
	)
)

# Never shown in a document, regardless of layout.
UNSHOWN_FIELDTYPES = frozenset(
	(
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Image",
		"Fold",
		"Heading",
		"Password",
		"Attach",
		"Attach Image",
		"Signature",
		"Geolocation",
		"JSON",
		"Code",
		"Barcode",
		"Icon",
		"Color",
		"Rating",
		"Table MultiSelect",
		"Duration",
		"Dynamic Link",
	)
)

SYSTEM_FIELDNAMES = frozenset(
	(
		"naming_series",
		"amended_from",
		"docstatus",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
		"workflow_state",
		"letter_head",
		"select_print_heading",
		"language",
		"title",
		"status",
		"is_return",
		"disabled",
		"_user_tags",
		"_comments",
		"_assign",
		"_liked_by",
		"_seen",
		"doctype",
	)
)


_UNSAFE_CSS = re.compile(r"[a-z-]+\s*:\s*[^;\"']*(url\(|expression\()[^;\"']*;?", re.IGNORECASE)


def clean_html(html):
	"""sanitize_html plus removal of CSS that can load external resources."""
	return _UNSAFE_CSS.sub("", sanitize_html(cstr(html)))


def json_safe(value):
	if isinstance(value, Decimal):
		return float(value)
	if isinstance(value, datetime.datetime | datetime.date | datetime.time | datetime.timedelta):
		return str(value)
	return value


def is_empty(value, df):
	if value is None or value == "":
		return True
	if df.fieldtype in NUMERIC or df.fieldtype == "Check":
		return not flt(value)
	if df.fieldtype in RICH:
		return not frappe.utils.strip_html(cstr(value)).strip()
	return False


def resolve_currency(df, row, parent=None):
	opt = cstr(df.options)
	currency = None
	if opt and ":" not in opt:
		currency = (row.get(opt) if row else None) or (parent.get(opt) if parent else None)
		if not currency and frappe.db.exists("Currency", opt):
			currency = opt
	elif opt.count(":") == 2:
		link_dt, link_field, currency_field = opt.split(":")
		source = row.get(link_field) or (parent.get(link_field) if parent else None)
		if source:
			currency = frappe.get_cached_value(link_dt, source, currency_field)
	return (
		currency
		or (parent.get("currency") if parent else None)
		or (row.get("currency") if row else None)
		or frappe.db.get_default("currency")
	)


def format_display(value, df, row=None, parent=None):
	"""Human text for a field value. Rich text is returned as sanitized HTML."""
	if value is None or value == "":
		return ""
	ft = df.fieldtype
	if ft == "Currency":
		return fmt_money(
			flt(value), precision=cint(df.precision) or None, currency=resolve_currency(df, row, parent)
		)
	if ft == "Check":
		return _("Yes") if cint(value) else _("No")
	if ft in RICH:
		return clean_html(value)
	if ft in MULTILINE or ft in ("Data", "Phone", "Read Only", "Autocomplete"):
		return cstr(value)
	if ft == "Select":
		return _(cstr(value))
	if ft == "Link" and df.options:
		return link_title(df.options, value)
	return cstr(format_value(value, df=df, doc=row or parent, currency=None))


def link_title(doctype, value, force=False):
	"""Title of a linked record when the DocType shows titles in links (or ``force``)."""
	if not hasattr(frappe.local, "docstudio_link_titles"):
		frappe.local.docstudio_link_titles = {}
	cache = frappe.local.docstudio_link_titles
	key = (doctype, cstr(value), force)
	if key not in cache:
		title = None
		try:
			meta = frappe.get_meta(doctype)
			if meta.title_field and meta.title_field != "name" and (force or meta.show_title_field_in_link):
				title = frappe.db.get_value(doctype, value, meta.title_field)
		except Exception:
			title = None
		cache[key] = cstr(title or value)
	return cache[key]


def coerce(value, df):
	"""Convert a value sent by the browser into the DocField's type; throws on bad input."""
	ft = df.fieldtype
	if value is None:
		return None
	if ft in ("Int", "Long Int", "Check"):
		return cint(value)
	if ft in ("Float", "Currency", "Percent"):
		return flt(value)
	if value == "":
		return None if ft in ("Date", "Datetime", "Time", "Link") else ""
	if ft == "Date":
		return str(getdate(value))
	if ft == "Datetime":
		return str(get_datetime(value))
	if ft == "Time":
		return str(get_time(value))
	if ft == "Select":
		options = [o for o in cstr(df.options).split("\n")]
		if cstr(value) not in options:
			frappe.throw(_("{0} is not a valid option for {1}.").format(cstr(value), _(df.label)))
		return cstr(value)
	if ft in RICH:
		return clean_html(value)
	return cstr(value)
