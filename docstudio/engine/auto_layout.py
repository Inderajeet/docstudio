"""Auto layout: a business document for any DocType, built only from its meta."""

import frappe
from frappe import _

from docstudio.engine import model as m
from docstudio.engine.company import get_company_info, html_to_text
from docstudio.engine.formatting import (
	NUMERIC,
	RICH,
	SYSTEM_FIELDNAMES,
	UNSHOWN_FIELDTYPES,
	is_empty,
	link_title,
)
from docstudio.engine.highlights import is_total_field

MAX_TABLE_COLUMNS = 8

PARTY_DETAIL_FIELDS = (
	"address_display",
	"customer_address_display",
	"supplier_address_display",
	"shipping_address",
	"contact_display",
	"contact_mobile",
	"contact_email",
	"billing_address_gstin",
	"customer_gstin",
	"supplier_gstin",
	"tax_id",
)
PARTY_CONSUMED_EXTRA = (
	"customer_address",
	"supplier_address",
	"contact_person",
	"shipping_address_name",
	"customer_name",
	"supplier_name",
	"party_name",
	"party_type",
	"quotation_to",
)
SECONDARY_DATES = ("due_date", "valid_till", "schedule_date", "delivery_date", "expected_delivery_date")
COMPANY_CONSUMED = ("company_address", "company_address_display", "company_gstin", "letter_head")


def build_sections(ctx):
	doc, hl = ctx.doc, ctx.highlights
	consumed = set()
	sections = []

	company = get_company_info(doc, hl.get("company_field"))
	if company:
		sections.append(letterhead_section(ctx, company))
		consumed.update((hl["company_field"], *COMPANY_CONSUMED))

	sections.append(title_section(ctx))
	if hl.get("title_field"):
		consumed.add(hl["title_field"])

	sections.append(header_section(ctx, consumed))

	totals = totals_section(ctx, consumed)
	body = body_sections(ctx, consumed)

	if totals:
		anchor = main_table_index(body)
		if anchor is None:
			body.append(totals)
		else:
			body.insert(anchor + 1, totals)
	sections.extend(body)

	if company:
		sections.append(signature_section(ctx, company))
	return sections


def main_table_index(sections):
	"""The table totals belong under: ``items`` if present, else the biggest table with amounts."""
	tables = [(i, s) for i, s in enumerate(sections) if s["type"] == "table"]
	if not tables:
		return None
	for i, s in tables:
		if s["table"] == "items":
			return i
	with_amounts = [(i, s) for i, s in tables if any(c["fieldtype"] in NUMERIC for c in s["columns"])]
	i, _s = max(with_amounts or tables, key=lambda pair: (len(pair[1]["rows"]), -pair[0]))
	return i


def letterhead_section(ctx, company):
	return m.section(
		"s:letterhead",
		"letterhead",
		company={
			"name": ctx.text("lh:name", company["name"], style={"bold": True}),
			"lines": [ctx.text(f"lh:line:{i}", line) for i, line in enumerate(company["lines"])],
			"logo": company["logo"],
		},
	)


def title_section(ctx):
	doc = ctx.doc
	heading = ctx.text("title:heading", _(doc.doctype).upper(), style={"bold": True})
	subtitle = None
	title_field = ctx.highlights.get("title_field")
	title_value = doc.get(title_field) if title_field else None
	party_value = doc.get(ctx.highlights.get("party_field") or "")
	if title_value and title_value not in (doc.name, party_value):
		subtitle = ctx.field_node(title_field, label="")
	return m.section("s:title", "title", heading=heading, subtitle=subtitle)


def _party_display_field(meta, party_field):
	"""customer -> customer_name when both exist (the Link holds an ID, the name is nicer)."""
	df = meta.get_field(party_field)
	if df and df.fieldtype == "Link":
		companion = f"{party_field}_name"
		cdf = meta.get_field(companion)
		if cdf and not cdf.hidden:
			return companion
	return party_field


def header_section(ctx, consumed):
	doc, meta, hl = ctx.doc, ctx.meta, ctx.highlights
	left = None
	party_field = hl.get("party_field")
	if party_field and doc.get(party_field):
		shown = _party_display_field(meta, party_field)
		if not doc.get(shown):
			shown = party_field
		items = [ctx.field_node(shown, label="")]
		items[0]["style"] = {"bold": True}
		sdf = meta.get_field(shown)
		if sdf.fieldtype == "Link" and sdf.options:
			items[0]["display"] = link_title(sdf.options, doc.get(shown), force=True)
		consumed.update((party_field, shown, *PARTY_CONSUMED_EXTRA))
		for fieldname in PARTY_DETAIL_FIELDS:
			df = meta.get_field(fieldname)
			if not df or df.hidden or fieldname in consumed or is_empty(doc.get(fieldname), df):
				continue
			if df.fieldtype in RICH or fieldname.endswith("_display"):
				node = ctx.text(m.field_id(fieldname), html_to_text(doc.get(fieldname)), label="")
				node["multiline"] = True
			else:
				node = ctx.field_node(fieldname)
			items.append(node)
			consumed.add(fieldname)
		left = {"title": _("To"), "items": items}

	right = [ctx.text("hdr:number", doc.name, label=_("No."))]
	date_field = hl.get("date_field")
	if date_field and doc.get(date_field):
		right.append(ctx.field_node(date_field))
		consumed.add(date_field)
	for fieldname in SECONDARY_DATES:
		df = meta.get_field(fieldname)
		if df and fieldname not in consumed and not df.hidden and not df.print_hide and doc.get(fieldname):
			right.append(ctx.field_node(fieldname))
			consumed.add(fieldname)
	return m.section("s:header", "header", left=left, right={"items": right})


def _skip(ctx, df, consumed):
	return (
		df.hidden
		or df.print_hide
		or df.fieldtype in UNSHOWN_FIELDTYPES
		or df.fieldname in SYSTEM_FIELDNAMES
		or df.fieldname in consumed
		or is_empty(ctx.doc.get(df.fieldname), df)
	)


def body_sections(ctx, consumed):
	out = []
	state = {"cur": None}

	def start(key, label=None):
		state["cur"] = {"key": key, "label": label, "columns": [[]]}

	def flush():
		cur = state["cur"]
		cols = [c for c in cur["columns"] if c]
		if cols:
			out.append(
				m.section(
					f"s:{cur['key']}",
					"fields",
					label=_(cur["label"]) if cur["label"] else None,
					columns=cols,
					boxed=len(cols) > 1,
				)
			)

	start("main")
	for df in ctx.meta.fields:
		ft = df.fieldtype
		if ft in ("Section Break", "Tab Break"):
			flush()
			start(df.fieldname, df.label)
			continue
		if ft == "Column Break":
			state["cur"]["columns"].append([])
			continue
		if ft == "Table":
			if df.hidden or df.print_hide or df.fieldname in consumed:
				continue
			table = table_section(ctx, df)
			if table:
				flush()
				out.append(table)
				start(f"{df.fieldname}_after")
			continue
		if _skip(ctx, df, consumed):
			continue
		if ft in RICH:
			flush()
			out.append(
				m.section(
					f"s:rt:{df.fieldname}", "rich_text", label=_(df.label), node=ctx.field_node(df.fieldname)
				)
			)
			start(f"{df.fieldname}_after")
			continue
		state["cur"]["columns"][-1].append(ctx.field_node(df.fieldname))
	flush()
	return out


def table_columns(child_meta, rows=None, limit=MAX_TABLE_COLUMNS):
	def shown(df):
		return not (
			df.hidden or df.print_hide or df.fieldtype in UNSHOWN_FIELDTYPES or df.fieldtype == "Table"
		)

	cols = [df for df in child_meta.fields if df.in_list_view and shown(df)]
	if len(cols) < 2:
		for df in child_meta.fields:
			if len(cols) >= 6:
				break
			if df not in cols and shown(df) and df.fieldname not in SYSTEM_FIELDNAMES:
				cols.append(df)
	if rows is not None:
		cols = [df for df in cols if any(not is_empty(r.get(df.fieldname), df) for r in rows)] or cols[:1]
	return cols[:limit]


def table_section(ctx, table_df, columns=None, label=None, section_id=None):
	rows = ctx.doc.get(table_df.fieldname) or []
	can_edit = ctx.table_rows_editable(table_df)
	if not rows and not can_edit:
		return None
	child_meta = frappe.get_meta(table_df.options)
	cols = columns or table_columns(child_meta, rows if not can_edit else None)
	if not cols:
		return None
	return m.section(
		section_id or f"s:tbl:{table_df.fieldname}",
		"table",
		label=label if label is not None else _(table_df.label),
		table=table_df.fieldname,
		columns=[
			{
				"field": df.fieldname,
				"label": _(df.label),
				"fieldtype": df.fieldtype,
				"align": "right" if df.fieldtype in ("Currency", "Float", "Int", "Percent") else None,
			}
			for df in cols
		],
		rows=[
			{"name": r.name, "cells": [ctx.cell_node(table_df.fieldname, r, df) for df in cols]} for r in rows
		],
		can_edit_rows=can_edit,
		preview_only=not rows,
	)


def totals_section(ctx, consumed):
	doc, meta = ctx.doc, ctx.meta
	grand = ctx.highlights.get("total_field")
	fields = [
		df
		for df in meta.fields
		if (is_total_field(df) or df.fieldname == grand)
		and not df.hidden
		and not df.print_hide
		and df.fieldname not in consumed
		and not is_empty(doc.get(df.fieldname), df)
	]
	if not fields:
		return None
	items = []
	for df in fields:
		node = ctx.field_node(df.fieldname)
		if df.fieldname == grand:
			node["style"] = {"bold": True}
			node["grand"] = True
		items.append(node)
		consumed.add(df.fieldname)
	# The grand total always goes last.
	items.sort(key=lambda n: bool(n.get("grand")))
	return m.section("s:totals", "totals", items=items)


def signature_section(ctx, company):
	return m.section(
		"s:signature",
		"signature",
		lines=[
			ctx.text("sig:for", _("For {0}").format(company["name"]), style={"bold": True}),
			ctx.text("sig:title", _("Authorized Signatory")),
		],
	)
