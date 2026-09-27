"""Test fixtures: custom DocTypes created at test time (never shipped to sites)."""

import frappe

TEST_COMPANY = "DocStudio Test Company"
TEST_CHILD = "DocStudio Test Item"
TEST_DT = "DocStudio Test Record"

TAMIL = "தமிழ் வாடிக்கையாளர்"

PERMS = [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]


def _doctype(name, fields, **kw):
	if frappe.db.exists("DocType", name):
		return
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": name,
			"module": "Custom",
			"custom": 1,
			"fields": fields,
			"permissions": [] if kw.get("istable") else PERMS,
			**kw,
		}
	).insert(ignore_permissions=True)


def ensure_test_doctypes():
	if not frappe.db.exists("Currency", "INR"):
		# Fresh Frappe-only sites may not have run the setup wizard yet.
		frappe.get_doc(
			{"doctype": "Currency", "currency_name": "INR", "symbol": "₹", "fraction": "Paisa", "enabled": 1}
		).insert(ignore_permissions=True)
	_doctype(
		TEST_COMPANY,
		[
			{"fieldname": "company_name", "fieldtype": "Data", "label": "Company Name", "reqd": 1},
			{"fieldname": "address", "fieldtype": "Small Text", "label": "Address"},
			{"fieldname": "phone_no", "fieldtype": "Data", "label": "Phone"},
			{"fieldname": "email", "fieldtype": "Data", "label": "Email"},
			{"fieldname": "tax_id", "fieldtype": "Data", "label": "Tax ID"},
		],
		autoname="field:company_name",
	)
	_doctype(
		TEST_CHILD,
		[
			{"fieldname": "item_name", "fieldtype": "Data", "label": "Item", "in_list_view": 1},
			{"fieldname": "description", "fieldtype": "Text Editor", "label": "Description"},
			{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "in_list_view": 1},
			{
				"fieldname": "rate",
				"fieldtype": "Currency",
				"label": "Rate",
				"in_list_view": 1,
				"options": "currency",
			},
			{
				"fieldname": "amount",
				"fieldtype": "Currency",
				"label": "Amount",
				"in_list_view": 1,
				"read_only": 1,
				"options": "currency",
			},
			{
				"fieldname": "secret_note",
				"fieldtype": "Data",
				"label": "Secret Note",
				"in_list_view": 1,
				"print_hide": 1,
			},
			{
				"fieldname": "hidden_code",
				"fieldtype": "Data",
				"label": "Hidden Code",
				"in_list_view": 1,
				"hidden": 1,
			},
		],
		istable=1,
	)
	_doctype(
		TEST_DT,
		[
			{"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": TEST_COMPANY},
			{"fieldname": "customer_name", "fieldtype": "Data", "label": "Customer Name"},
			{"fieldname": "posting_date", "fieldtype": "Date", "label": "Posting Date"},
			{
				"fieldname": "currency",
				"fieldtype": "Link",
				"label": "Currency",
				"options": "Currency",
				"print_hide": 1,
			},
			{"fieldname": "details_section", "fieldtype": "Section Break", "label": "Details"},
			{"fieldname": "reference_no", "fieldtype": "Data", "label": "Reference No"},
			{"fieldname": "priority", "fieldtype": "Select", "label": "Priority", "options": "\nLow\nHigh"},
			{"fieldname": "details_col", "fieldtype": "Column Break"},
			{"fieldname": "site_name", "fieldtype": "Data", "label": "Site"},
			{"fieldname": "is_urgent", "fieldtype": "Check", "label": "Urgent"},
			{"fieldname": "empty_section", "fieldtype": "Section Break", "label": "Nothing Here"},
			{"fieldname": "unused_field", "fieldtype": "Data", "label": "Unused"},
			{"fieldname": "items_section", "fieldtype": "Section Break", "label": "Items"},
			{"fieldname": "items", "fieldtype": "Table", "label": "Items", "options": TEST_CHILD},
			{"fieldname": "totals_section", "fieldtype": "Section Break", "label": "Totals"},
			{
				"fieldname": "grand_total",
				"fieldtype": "Currency",
				"label": "Grand Total",
				"read_only": 1,
				"options": "currency",
			},
			{"fieldname": "internal_ref", "fieldtype": "Data", "label": "Internal Ref", "hidden": 1},
			{
				"fieldname": "print_hidden_ref",
				"fieldtype": "Data",
				"label": "Print Hidden Ref",
				"print_hide": 1,
			},
			{"fieldname": "notes_section", "fieldtype": "Section Break", "label": "Notes"},
			{"fieldname": "notes", "fieldtype": "Text Editor", "label": "Notes"},
		],
		autoname="format:DST-{#####}",
		title_field="customer_name",
	)
	if not frappe.db.exists(TEST_COMPANY, "Acme Test Traders"):
		frappe.get_doc(
			{
				"doctype": TEST_COMPANY,
				"company_name": "Acme Test Traders",
				"address": "12 Anna Salai\nChennai 600002",
				"phone_no": "+91 44 1234 5678",
				"email": "sales@acme.test",
				"tax_id": "33ABCDE1234F1Z5",
			}
		).insert(ignore_permissions=True)


def reset_templates():
	"""Remove templates for the test DocType (rolled back with the test transaction)."""
	for name in frappe.get_all("DocStudio Template", filters={"reference_doctype": TEST_DT}, pluck="name"):
		frappe.delete_doc("DocStudio Template", name, force=True, ignore_permissions=True)


def make_record(**overrides):
	ensure_test_doctypes()
	reset_templates()
	data = {
		"doctype": TEST_DT,
		"company": "Acme Test Traders",
		"customer_name": "Bharat Builders",
		"posting_date": "2026-09-01",
		"currency": "INR",
		"reference_no": "REF-77",
		"priority": "High",
		"site_name": "Velachery",
		"is_urgent": 1,
		"grand_total": 4371,
		"internal_ref": "SHOULD-NOT-SHOW",
		"print_hidden_ref": "ALSO-HIDDEN",
		"notes": "<p>Deliver <strong>before</strong> noon.</p>",
		"items": [
			{
				"item_name": "Cement",
				"qty": 3,
				"rate": 1000,
				"amount": 3000,
				"secret_note": "x",
				"hidden_code": "y",
				"description": "<p>OPC 53 grade</p>",
			},
			{"item_name": "Sand", "qty": 1, "rate": 1371, "amount": 1371},
		],
	}
	data.update(overrides)
	return frappe.get_doc(data).insert(ignore_permissions=True)
