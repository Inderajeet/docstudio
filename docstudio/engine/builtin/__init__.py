"""Built-in (hand-designed) templates shipped with DocStudio."""

from docstudio.engine.builtin import layouts

_COMMERCIAL_TABLES = {"item_": "items_table", "tax_": "taxes_table"}

BUILTINS = {
	"quotation": {
		"doctype": "Quotation",
		"template_name": "Quotation (Standard)",
		"builder": layouts.quotation,
		"slots": layouts.QUOTATION_SLOTS,
		"requires": ["items", "grand_total", "transaction_date"],
		"slot_tables": _COMMERCIAL_TABLES,
	},
	"sales_invoice": {
		"doctype": "Sales Invoice",
		"template_name": "Sales Invoice (GST)",
		"builder": layouts.sales_invoice,
		"slots": layouts.SALES_INVOICE_SLOTS,
		"requires": ["items", "grand_total", "posting_date"],
		"slot_tables": _COMMERCIAL_TABLES,
	},
	"purchase_order": {
		"doctype": "Purchase Order",
		"template_name": "Purchase Order (Standard)",
		"builder": layouts.purchase_order,
		"slots": layouts.PURCHASE_ORDER_SLOTS,
		"requires": ["items", "grand_total", "transaction_date"],
		"slot_tables": _COMMERCIAL_TABLES,
	},
	"delivery_note": {
		"doctype": "Delivery Note",
		"template_name": "Delivery Note (Standard)",
		"builder": layouts.delivery_note,
		"slots": layouts.DELIVERY_NOTE_SLOTS,
		"requires": ["items", "posting_date"],
		"slot_tables": {"item_": "items_table"},
	},
	"job_offer": {
		"doctype": "Job Offer",
		"template_name": "Job Offer Letter",
		"builder": layouts.job_offer,
		"slots": layouts.JOB_OFFER_SLOTS,
		"requires": ["applicant_name"],
		"slot_tables": {"term_": "offer_terms_table"},
		"theme": "Formal",
	},
}


def is_applicable(entry):
	import frappe

	if not frappe.db.exists("DocType", entry["doctype"]):
		return False
	meta = frappe.get_meta(entry["doctype"])
	return all(meta.has_field(f) for f in entry.get("requires", []))


def slot_scope(entry, slot):
	"""The table slot a child-column slot belongs to, else None (parent field)."""
	for prefix, table_slot in (entry.get("slot_tables") or {}).items():
		if slot.startswith(prefix) and slot != table_slot:
			return table_slot
	return None
