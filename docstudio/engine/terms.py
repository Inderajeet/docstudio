"""Terms Blocks: reusable clauses a user drops into a document from the preview."""

import frappe
from frappe import _

from docstudio.engine import model as m
from docstudio.engine.formatting import clean_html

SECTION_ID = "s:terms_block"
NODE_ID = "terms:block"


def applicable_blocks(doctype):
	blocks = frappe.get_all(
		"DocStudio Terms Block", filters={"enabled": 1}, fields=["name", "title"], order_by="title asc"
	)
	scoped = {}
	for row in frappe.get_all(
		"DocStudio Terms DocType",
		filters={"parenttype": "DocStudio Terms Block", "parentfield": "applicable_doctypes"},
		fields=["parent", "document_type"],
	):
		scoped.setdefault(row.parent, set()).add(row.document_type)
	return [b for b in blocks if b.name not in scoped or doctype in scoped[b.name]]


def chosen_block(template, patch):
	"""The block for this document: explicit choice in the patch, else the template default."""
	layout = patch.get("layout") or {}
	if "terms_block" in layout:
		return layout.get("terms_block") or None
	return template.default_terms if template else None


def insert_terms_block(model, ctx, template, patch):
	name = chosen_block(template, patch)
	if not name or not frappe.db.get_value("DocStudio Terms Block", name, "enabled"):
		return
	if name not in {b.name for b in applicable_blocks(ctx.doc.doctype)}:
		return
	block = frappe.get_cached_doc("DocStudio Terms Block", name)
	node = m.text_node(NODE_ID, clean_html(block.content), editable=ctx.preview, html=True)
	section = m.section(SECTION_ID, "terms", label=_("Terms and Conditions"), node=node, block=name)
	sections = model["sections"]
	sig = next((i for i, s in enumerate(sections) if s["type"] == "signature"), len(sections))
	sections.insert(sig, section)
