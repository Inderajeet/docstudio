"""Built-in layouts: Quotation, Sales Invoice, Purchase Order, Delivery Note, Job Offer."""

from frappe import _

from docstudio.engine import model as m
from docstudio.engine.builtin import common as c


PARTY_SLOTS = {
	"company": ("company", "Company whose letterhead and signature are used"),
	"party_address": ("address_display", "Party address (display field)"),
	"party_contact": ("contact_display", "Contact person"),
	"party_tax_id": ("tax_id", "Party GSTIN / tax ID"),
}
ITEM_SLOTS = {
	"items_table": ("items", "Items child table"),
	"item_name": ("item_name", "Item column"),
	"item_description": ("", "Optional description column (e.g. description)"),
	"item_hsn": ("gst_hsn_code", "HSN/SAC column (shown when filled)"),
	"item_qty": ("qty", "Quantity column"),
	"item_uom": ("uom", "Unit column"),
	"item_rate": ("rate", "Rate column"),
	"item_amount": ("amount", "Amount column"),
}
TOTAL_SLOTS = {
	"taxes_table": ("taxes", "Taxes child table"),
	"tax_description": ("description", "Tax row label"),
	"tax_amount": ("tax_amount", "Tax row amount"),
	"net_total": ("net_total", "Net total (shown when there are taxes)"),
	"grand_total": ("grand_total", "Grand total"),
	"rounded_total": ("rounded_total", "Rounded total (shown when different)"),
	"in_words": ("in_words", "Amount in words"),
	"terms": ("terms", "Terms and conditions"),
}


def _slots(*groups, **extra):
	out = {}
	for g in groups:
		out.update(g)
	out.update(extra)
	return out


def _item_columns(with_prices=True):
	cols = [
		("item_name", _("Description")),
		("item_description", _("Details")),
		("item_hsn", _("HSN/SAC")),
		("item_qty", _("Qty")),
		("item_uom", _("Unit")),
	]
	if with_prices:
		cols += [("item_rate", _("Rate")), ("item_amount", _("Amount"))]
	return cols


def _commercial(
	ctx,
	defaults,
	heading,
	left_title,
	party_slot,
	right_slots,
	extra_details=(),
	with_prices=True,
	tax_label=None,
):
	slots = c.Slots(ctx, defaults)
	letterhead, company = c.letterhead(ctx, slots)
	sections = [
		letterhead,
		c.title(ctx, heading),
		c.header(
			ctx,
			slots,
			left_title,
			[
				(party_slot, "", False),
				("party_address", "", True),
				("party_contact", _("Contact"), False),
				("party_tax_id", tax_label or _("Tax ID"), False),
			],
			right_slots,
		),
		c.details(ctx, slots, extra_details),
		c.items_table(ctx, slots, "items_table", _item_columns(with_prices)),
	]
	if with_prices:
		sections += [c.totals(ctx, slots), c.in_words(ctx, slots)]
	sections += [c.terms(ctx, slots), c.signature(ctx, company)]
	return c.compact(sections)


QUOTATION_SLOTS = _slots(
	PARTY_SLOTS,
	ITEM_SLOTS,
	TOTAL_SLOTS,
	party=("customer_name", "Customer / lead name"),
	date=("transaction_date", "Quotation date"),
	valid_till=("valid_till", "Valid till"),
)


def quotation(ctx):
	return _commercial(
		ctx,
		QUOTATION_SLOTS,
		_("QUOTATION"),
		_("Quotation To"),
		"party",
		[("date", _("Date")), ("valid_till", _("Valid Till"))],
	)


SALES_INVOICE_SLOTS = _slots(
	PARTY_SLOTS,
	ITEM_SLOTS,
	TOTAL_SLOTS,
	party=("customer_name", "Customer name"),
	party_tax_id=("billing_address_gstin", "Customer GSTIN (falls back to nothing when empty)"),
	date=("posting_date", "Invoice date"),
	due_date=("due_date", "Due date"),
	customer_po=("po_no", "Customer's purchase order number"),
	place_of_supply=("place_of_supply", "Place of supply"),
	shipping_address=("shipping_address", "Shipping address (display field)"),
)


def sales_invoice(ctx):
	return _commercial(
		ctx,
		SALES_INVOICE_SLOTS,
		_("TAX INVOICE"),
		_("Bill To"),
		"party",
		[("date", _("Invoice Date")), ("due_date", _("Due Date")), ("customer_po", _("Customer PO"))],
		extra_details=[("place_of_supply", _("Place of Supply")), ("shipping_address", _("Ship To"))],
		tax_label=_("GSTIN"),
	)


PURCHASE_ORDER_SLOTS = _slots(
	PARTY_SLOTS,
	ITEM_SLOTS,
	TOTAL_SLOTS,
	party=("supplier_name", "Supplier name"),
	party_tax_id=("supplier_gstin", "Supplier GSTIN"),
	date=("transaction_date", "Order date"),
	required_by=("schedule_date", "Required by"),
	deliver_to=("shipping_address_display", "Delivery address (display field)"),
)


def purchase_order(ctx):
	return _commercial(
		ctx,
		PURCHASE_ORDER_SLOTS,
		_("PURCHASE ORDER"),
		_("Supplier"),
		"party",
		[("date", _("PO Date")), ("required_by", _("Required By"))],
		extra_details=[("deliver_to", _("Deliver To"))],
	)


DELIVERY_NOTE_SLOTS = _slots(
	PARTY_SLOTS,
	ITEM_SLOTS,
	{"terms": TOTAL_SLOTS["terms"]},
	party=("customer_name", "Customer name"),
	date=("posting_date", "Delivery date"),
	customer_po=("po_no", "Customer's purchase order number"),
	ship_to=("shipping_address", "Shipping address (display field)"),
	transporter=("transporter_name", "Transporter"),
	vehicle_no=("vehicle_no", "Vehicle number"),
	lr_no=("lr_no", "Transport receipt (LR) number"),
)


def delivery_note(ctx):
	return _commercial(
		ctx,
		DELIVERY_NOTE_SLOTS,
		_("DELIVERY NOTE"),
		_("Deliver To"),
		"party",
		[("date", _("Date")), ("customer_po", _("Customer PO"))],
		extra_details=[
			("ship_to", _("Ship To")),
			("transporter", _("Transporter")),
			("vehicle_no", _("Vehicle No.")),
			("lr_no", _("LR No.")),
		],
		with_prices=False,
	)


JOB_OFFER_SLOTS = {
	"company": ("company", "Company"),
	"applicant": ("applicant_name", "Applicant name"),
	"applicant_email": ("applicant_email", "Applicant email"),
	"date": ("offer_date", "Offer date"),
	"designation": ("designation", "Designation"),
	"offer_terms_table": ("offer_terms", "Offer terms child table"),
	"term_label": ("offer_term", "Offer term column"),
	"term_value": ("value", "Offer term value column"),
	"terms": ("terms", "Terms and conditions"),
}


def job_offer(ctx):
	slots = c.Slots(ctx, JOB_OFFER_SLOTS)
	letterhead, company = c.letterhead(ctx, slots)
	applicant = slots.value("applicant") or ""
	designation = slots.value("designation") or ""
	company_name = company["name"] if company else (slots.value("company") or "")

	subject = ctx.text(
		"letter:subject",
		_("Offer of Employment: {0}").format(designation) if designation else _("Offer of Employment"),
		style={"bold": True},
	)
	subject["editable"] = ctx.preview
	body = ctx.text(
		"letter:body",
		"".join(
			(
				f"<p>{_('Dear {0},').format(frappe_escape(applicant) or _('Candidate'))}</p>",
				"<p>"
				+ _("We are pleased to offer you the position of <strong>{0}</strong> at {1}.").format(
					frappe_escape(designation), frappe_escape(company_name)
				)
				+ " "
				+ _("The key terms of this offer are set out below.")
				+ "</p>",
				"<p>"
				+ _("Please sign and return a copy of this letter to confirm your acceptance.")
				+ "</p>",
			)
		),
		html=True,
	)
	body["editable"] = ctx.preview  # letter text is always editable; kept with the document version

	sections = [
		letterhead,
		c.header(
			ctx,
			slots,
			_("To"),
			[("applicant", "", False), ("applicant_email", "", False)],
			[("date", _("Date"))],
		),
		m.section("s:subject", "text", label=None, node=subject),
		m.section("s:body", "text", label=None, node=body),
		c.items_table(
			ctx,
			slots,
			"offer_terms_table",
			[("term_label", _("Term")), ("term_value", _("Details"))],
			section_id="s:offer_terms",
		),
		c.terms(ctx, slots),
		c.signature(ctx, company),
	]
	return c.compact(sections)


def frappe_escape(value):
	from frappe.utils import escape_html

	return escape_html(value or "")
