"""Which field is the title / party / date / total / company of a record.

Template settings win; otherwise we guess from fieldnames and labels.
"""

import re

from docstudio.engine.formatting import NUMERIC

HIGHLIGHT_KEYS = ("title_field", "party_field", "date_field", "total_field", "company_field")

PARTY_NAMES = (
	"customer_name",
	"supplier_name",
	"party_name",
	"employee_name",
	"applicant_name",
	"student_name",
	"patient_name",
	"member_name",
	"contact_name",
	"lead_name",
	"vendor_name",
	"customer",
	"supplier",
	"party",
	"employee",
	"vendor",
	"client",
	"client_name",
)
DATE_NAMES = (
	"posting_date",
	"transaction_date",
	"date",
	"offer_date",
	"appointment_date",
	"po_date",
	"order_date",
	"invoice_date",
	"bill_date",
	"schedule_date",
)
TOTAL_NAMES = (
	"rounded_total",
	"grand_total",
	"total_amount",
	"net_total",
	"total",
	"amount",
	"base_grand_total",
)
_TOTAL_RE = re.compile(r"(^|_)(grand_|net_|rounded_)?total(_amount)?$")


def _usable(meta, fieldname):
	df = meta.get_field(fieldname) if fieldname else None
	return df if df and not df.hidden else None


def guess_title(meta):
	return meta.title_field if _usable(meta, meta.title_field) else None


def guess_party(meta):
	for name in PARTY_NAMES:
		if _usable(meta, name):
			return name
	for df in meta.fields:
		if df.fieldtype == "Link" and df.options in (
			"Customer",
			"Supplier",
			"Employee",
			"Lead",
			"Job Applicant",
		):
			return df.fieldname
	return None


def guess_date(meta):
	for name in DATE_NAMES:
		df = _usable(meta, name)
		if df and df.fieldtype in ("Date", "Datetime"):
			return name
	for df in meta.fields:
		if df.fieldtype == "Date" and not df.hidden:
			return df.fieldname
	return None


def guess_total(meta):
	for name in TOTAL_NAMES:
		df = _usable(meta, name)
		if df and df.fieldtype in NUMERIC:
			return name
	return None


def guess_company(meta):
	df = _usable(meta, "company")
	if df and df.fieldtype == "Link":
		return "company"
	for df in meta.fields:
		if df.fieldtype == "Link" and df.options == "Company" and not df.hidden:
			return df.fieldname
	return None


def is_total_field(df):
	return df.fieldtype in ("Currency", "Float") and bool(_TOTAL_RE.search(df.fieldname))


def resolve(meta, template=None):
	"""Dict of highlight key -> fieldname (or None)."""
	chosen = {k: (template.get(k) if template else None) for k in HIGHLIGHT_KEYS}
	guesses = {
		"title_field": guess_title,
		"party_field": guess_party,
		"date_field": guess_date,
		"total_field": guess_total,
		"company_field": guess_company,
	}
	out = {}
	for key in HIGHLIGHT_KEYS:
		fieldname = chosen.get(key)
		out[key] = fieldname if _usable(meta, fieldname) else guesses[key](meta)
	return out
