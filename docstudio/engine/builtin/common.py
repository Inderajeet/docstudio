"""Building blocks for hand-designed templates.

Built-in layouts never read fieldnames directly: they ask for a *slot* (``ctx.mapped``) whose
default fieldname can be remapped per site in the template's Field Mapping table. Missing or
empty fields are simply left out, so a layout degrades gracefully on customised DocTypes.
"""

import frappe
from frappe import _

from docstudio.engine import auto_layout
from docstudio.engine import model as m
from docstudio.engine.company import get_company_info, html_to_text
from docstudio.engine.formatting import RICH, is_empty, link_title


class Slots:
	def __init__(self, ctx, defaults):
		self.ctx = ctx
		self.defaults = defaults  # slot -> (default fieldname, description)

	def fieldname(self, slot, meta=None):
		default = (self.defaults.get(slot) or (None, None))[0]
		fieldname = self.ctx.mapped(slot, default)
		meta = meta or self.ctx.meta
		return fieldname if fieldname and meta.has_field(fieldname) else None

	def df(self, slot, meta=None):
		fieldname = self.fieldname(slot, meta)
		return (meta or self.ctx.meta).get_field(fieldname) if fieldname else None

	def value(self, slot):
		fieldname = self.fieldname(slot)
		return self.ctx.doc.get(fieldname) if fieldname else None

	def node(self, slot, label=None, text=False):
		"""Value node for a parent-level slot, or None when unmapped/empty."""
		df = self.df(slot)
		if not df or is_empty(self.ctx.doc.get(df.fieldname), df):
			return None
		if text or df.fieldtype in RICH:
			# *_display address fields hold HTML; show them as plain lines.
			node = self.ctx.text(
				m.field_id(df.fieldname),
				html_to_text(self.ctx.doc.get(df.fieldname)),
				label=label if label is not None else "",
			)
			node["multiline"] = True
			return node
		node = self.ctx.field_node(df.fieldname, label=label)
		if df.fieldtype == "Link" and df.options:
			node["display"] = link_title(df.options, self.ctx.doc.get(df.fieldname), force=True)
		return node


def letterhead(ctx, slots):
	company_field = slots.fieldname("company") or ctx.highlights.get("company_field")
	company = get_company_info(ctx.doc, company_field)
	return (auto_layout.letterhead_section(ctx, company) if company else None), company


def title(ctx, text):
	return m.section(
		"s:title", "title", heading=ctx.text("title:heading", text, style={"bold": True}), subtitle=None
	)


def header(ctx, slots, left_title, party_slots, right_slots):
	"""Party box on the left (first slot bold), number + dates on the right."""
	left_items = []
	for i, (slot, label, as_text) in enumerate(party_slots):
		node = slots.node(slot, label=label, text=as_text)
		if node:
			if i == 0:
				node["style"] = {"bold": True}
			left_items.append(node)
	right = [ctx.text("hdr:number", ctx.doc.name, label=_("No."))]
	for slot, label in right_slots:
		node = slots.node(slot, label=label)
		if node:
			right.append(node)
	left = {"title": left_title, "items": left_items} if left_items else None
	return m.section("s:header", "header", left=left, right={"items": right})


def items_table(ctx, slots, table_slot, column_slots, label=None, section_id="s:items"):
	table_df = slots.df(table_slot)
	if not table_df or table_df.fieldtype != "Table":
		return None
	child_meta = frappe.get_meta(table_df.options)
	columns = []
	for slot, heading in column_slots:
		df = slots.df(slot, child_meta)
		if not df:
			continue
		if heading:
			df = frappe._dict(df.as_dict(), label=heading)
		columns.append(df)
	if not columns:
		return None
	rows = ctx.doc.get(table_df.fieldname) or []
	if rows and not ctx.table_rows_editable(table_df):
		# Drop columns that are empty on every row (e.g. HSN on a non-GST site).
		columns = [
			df for df in columns if any(not is_empty(r.get(df.fieldname), df) for r in rows)
		] or columns[:1]
	return auto_layout.table_section(ctx, table_df, columns=columns, label=label or "", section_id=section_id)


def totals(
	ctx,
	slots,
	net_slot="net_total",
	taxes_slot="taxes_table",
	grand_slot="grand_total",
	rounded_slot="rounded_total",
):
	items = []
	net = slots.node(net_slot)
	taxes_df = slots.df(taxes_slot)
	tax_rows = ctx.doc.get(taxes_df.fieldname) if taxes_df and taxes_df.fieldtype == "Table" else []
	if net and tax_rows:
		items.append(net)
	if tax_rows:
		child_meta = frappe.get_meta(taxes_df.options)
		desc_field = slots.fieldname("tax_description", child_meta)
		amount_df = slots.df("tax_amount", child_meta)
		for row in tax_rows:
			if not amount_df or is_empty(row.get(amount_df.fieldname), amount_df):
				continue
			node = ctx.cell_node(taxes_df.fieldname, row, amount_df)
			node["label"] = row.get(desc_field) if desc_field else amount_df.label
			items.append(node)
	grand = slots.node(grand_slot)
	rounded = slots.node(rounded_slot)
	if rounded and grand and rounded["value"] == grand["value"]:
		rounded = None
	final = rounded or grand
	if grand and rounded:
		items.append(grand)
	if final:
		final["style"] = {"bold": True}
		final["grand"] = True
		items.append(final)
	return m.section("s:totals", "totals", items=items) if items else None


def in_words(ctx, slots, slot="in_words"):
	node = slots.node(slot, label=_("Amount in Words"))
	return m.section("s:in_words", "fields", label=None, columns=[[node]], boxed=False) if node else None


def terms(ctx, slots, slot="terms", label=None):
	df = slots.df(slot)
	if not df or is_empty(ctx.doc.get(df.fieldname), df):
		return None
	return m.section(
		"s:terms", "terms", label=label or _("Terms and Conditions"), node=ctx.field_node(df.fieldname)
	)


def details(ctx, slots, pairs, label=None, section_id="s:details"):
	"""A single-column block of label/value rows for secondary details."""
	nodes = [n for n in (slots.node(slot, label=lbl) for slot, lbl in pairs) if n]
	if not nodes:
		return None
	half = (len(nodes) + 1) // 2
	columns = [nodes[:half], nodes[half:]] if len(nodes) > 2 else [nodes]
	return m.section(
		section_id, "fields", label=label, columns=[c for c in columns if c], boxed=len(columns) > 1
	)


def signature(ctx, company):
	return auto_layout.signature_section(ctx, company) if company else None


def compact(sections):
	return [s for s in sections if s]
