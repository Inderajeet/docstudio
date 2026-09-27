"""The edits patch: everything a user changed in the preview, as data."""

import copy
import json
import re

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from docstudio.engine import model as m
from docstudio.engine.formatting import TYPED_EDITABLE, clean_html, coerce

EMPTY = {
	"fields": {},
	"rows": {},
	"added_rows": {},
	"deleted_rows": {},
	"overrides": {},
	"styles": {},
	"layout": {},
}
RECORD_KEYS = ("fields", "rows", "added_rows", "deleted_rows")
NEW_ROW_PREFIX = "new-"

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ALIGN = ("left", "center", "right", "justify")


def normalize(patch):
	if isinstance(patch, str):
		patch = json.loads(patch or "{}")
	patch = patch or {}
	return {k: patch.get(k) if isinstance(patch.get(k), type(v)) else type(v)() for k, v in EMPTY.items()}


def has_record_changes(patch):
	return any(patch.get(k) for k in RECORD_KEYS)


def residual(patch):
	"""The part of a patch that never touches the record (formatting, overrides, layout)."""
	out = copy.deepcopy(patch)
	for k in RECORD_KEYS:
		out[k] = type(EMPTY[k])()
	return out


def is_empty_patch(patch):
	return not any(patch.get(k) for k in EMPTY)


def _field_df(meta, fieldname):
	df = meta.get_field(fieldname)
	if not df or df.fieldtype not in TYPED_EDITABLE or df.fieldtype == "Read Only":
		frappe.throw(_("Field {0} cannot be edited in DocStudio.").format(frappe.bold(fieldname)))
	return df


def _table_df(meta, fieldname):
	df = meta.get_field(fieldname)
	if not df or df.fieldtype != "Table":
		frappe.throw(_("{0} is not a table on {1}.").format(frappe.bold(fieldname), _(meta.name)))
	return df


def apply_to_doc(doc, patch, strict=False):
	"""Apply record changes to ``doc`` in memory."""
	from docstudio.engine.access import SAVE_TO_FORM
	from docstudio.engine.context import BuildContext

	ctx = BuildContext(doc, save_mode=SAVE_TO_FORM)
	meta = doc.meta

	def check(df, row=None):
		if strict and not ctx.field_writable(df, row):
			frappe.throw(_("You cannot change {0}.").format(frappe.bold(_(df.label))), frappe.PermissionError)

	for fieldname, value in patch["fields"].items():
		df = _field_df(meta, fieldname)
		check(df)
		doc.set(fieldname, coerce(value, df))

	for table, names in patch["deleted_rows"].items():
		tdf = _table_df(meta, table)
		if strict and not ctx.table_rows_editable(tdf):
			frappe.throw(_("You cannot remove rows from {0}.").format(_(tdf.label)), frappe.PermissionError)
		names = set(names or [])
		doc.set(table, [r for r in doc.get(table) if r.name not in names])
		for i, r in enumerate(doc.get(table), 1):
			r.idx = i

	for table, row_changes in patch["rows"].items():
		tdf = _table_df(meta, table)
		child_meta = frappe.get_meta(tdf.options)
		by_name = {r.name: r for r in doc.get(table)}
		for rowname, changes in (row_changes or {}).items():
			row = by_name.get(rowname)
			if not row:
				continue  # deleted meanwhile
			for fieldname, value in (changes or {}).items():
				df = _field_df(child_meta, fieldname)
				check(df, row)
				row.set(fieldname, coerce(value, df))

	for table, new_rows in patch["added_rows"].items():
		tdf = _table_df(meta, table)
		if strict and not ctx.table_rows_editable(tdf):
			frappe.throw(_("You cannot add rows to {0}.").format(_(tdf.label)), frappe.PermissionError)
		child_meta = frappe.get_meta(tdf.options)
		for new in new_rows or []:
			values = {}
			for fieldname, value in new.items():
				if fieldname == "name":
					continue
				df = _field_df(child_meta, fieldname)
				check(df, frappe._dict())
				values[fieldname] = coerce(value, df)
			row = doc.append(table, values)
			if not strict:
				# Temporary name so preview node ids stay stable; real names are assigned on save.
				row.name = cstr(new.get("name")) or f"{NEW_ROW_PREFIX}{row.idx}"
	return doc


def recalculate(doc, patch):
	"""Refresh computed values (amounts, totals) after in-memory edits, without saving."""
	for method in frappe.get_hooks("docstudio_recalculate"):
		frappe.get_attr(method)(doc)
	if hasattr(doc, "calculate_taxes_and_totals"):
		frappe.flags.mute_messages = True
		try:
			doc.calculate_taxes_and_totals()
		except Exception:
			pass
		finally:
			frappe.flags.mute_messages = False
		return
	touched = set(patch["rows"]) | set(patch["added_rows"]) | set(patch["deleted_rows"])
	for table in touched:
		for row in doc.get(table) or []:
			qty_field = (
				"qty" if row.meta.has_field("qty") else "quantity" if row.meta.has_field("quantity") else None
			)
			if qty_field and row.meta.has_field("rate") and row.meta.has_field("amount"):
				row.amount = flt(row.get(qty_field)) * flt(row.rate)


def clean_style(style):
	out = {}
	if not isinstance(style, dict):
		return out
	for key in ("bold", "italic", "underline"):
		if key in style:
			out[key] = bool(style[key])
	if style.get("size") is not None:
		size = flt(style["size"])
		if 6 <= size <= 72:
			out["size"] = size
	if isinstance(style.get("color"), str) and _COLOR.match(style["color"]):
		out["color"] = style["color"]
	if style.get("align") in _ALIGN:
		out["align"] = style["align"]
	return out


def clean_table_style(style):
	"""Per-table overrides set from the preview: {"table_style": "Bordered" | "Minimal"}."""
	from docstudio.engine.theme import TABLE_STYLES

	if isinstance(style, dict) and style.get("table_style") in TABLE_STYLES:
		return {"table_style": style["table_style"]}
	return {}


LAYOUT_LIST_KEYS = (
	"order",
	"hidden",
	"shown",
	"hidden_nodes",
	"shown_nodes",
	"hidden_columns",
	"shown_columns",
	"page_breaks",
)


def column_key(section_id, fieldname):
	return f"{section_id}:{fieldname}"


def apply_layout(model, layout):
	"""Section order, section/field/column visibility and page breaks."""
	if not layout:
		return
	sections = model["sections"]
	order = [sid for sid in layout.get("order") or [] if isinstance(sid, str)]
	if order:
		rank = {sid: i for i, sid in enumerate(order)}
		# Sections the saved order doesn't know about keep their place relative to their neighbours.
		positioned = sorted(
			enumerate(sections),
			key=lambda pair: (rank.get(pair[1]["id"], _neighbour_rank(sections, pair[0], rank)), pair[0]),
		)
		model["sections"] = sections = [s for _i, s in positioned]

	def toggles(hide_key, show_key):
		return set(layout.get(hide_key) or []), set(layout.get(show_key) or [])

	hidden, shown = toggles("hidden", "shown")
	hidden_cols, shown_cols = toggles("hidden_columns", "shown_columns")
	breaks = set(layout.get("page_breaks") or [])
	for s in sections:
		if s["id"] in hidden:
			s["hidden"] = True
		elif s["id"] in shown:
			s["hidden"] = False
		if s["id"] in breaks:
			s["style"] = {**(s.get("style") or {}), "page_break_before": True}
		for col in s.get("columns") or []:
			if isinstance(col, dict):
				key = column_key(s["id"], col["field"])
				if key in hidden_cols:
					col["hidden"] = True
				elif key in shown_cols:
					col["hidden"] = False
	hidden_nodes, shown_nodes = toggles("hidden_nodes", "shown_nodes")
	for node in m.iter_nodes(model):
		if node["id"] in hidden_nodes:
			node["hidden"] = True
		elif node["id"] in shown_nodes:
			node["hidden"] = False


def clean_layout(layout):
	"""Keep only known layout keys with string lists (used before storing on a template)."""
	out = {}
	for key in LAYOUT_LIST_KEYS:
		values = [v for v in (layout or {}).get(key) or [] if isinstance(v, str)]
		if values:
			out[key] = values
	return out


def _neighbour_rank(sections, index, rank):
	for j in range(index - 1, -1, -1):
		if sections[j]["id"] in rank:
			return rank[sections[j]["id"]] + 0.5
	return -0.5


def apply_to_model(model, patch):
	overrides = patch["overrides"]
	styles = patch["styles"]
	for node in m.iter_nodes(model):
		nid = node["id"]
		if nid in overrides:
			value = overrides[nid]
			if isinstance(value, dict):
				value = value.get("display")
			node["display"] = clean_html(value) if node.get("html") else cstr(value)
			node["overridden"] = True
		if nid in styles:
			node["style"] = {**(node.get("style") or {}), **clean_style(styles[nid])}
	for s in model["sections"]:
		sid = s["id"]
		if sid in styles:
			s["style"] = clean_style(styles[sid])
			if s["type"] == "table":
				table_style = clean_table_style(styles[sid])
				if table_style:
					s["table_style"] = table_style
		if s["type"] == "table":
			# Column formatting ("col:<section>:<field>") applies to every cell; a cell's own style wins.
			for i, col in enumerate(s["columns"]):
				col_style = clean_style(styles.get(column_style_id(sid, col["field"])))
				if not col_style:
					continue
				col["style"] = col_style
				for row in s["rows"]:
					cell = row["cells"][i]
					own = clean_style(styles.get(cell["id"]))
					cell["style"] = {**(cell.get("style") or {}), **col_style, **own}
	apply_layout(model, patch["layout"])
	return model


def column_style_id(section_id, fieldname):
	return f"col:{section_id}:{fieldname}"


def validate_patch_size(patch):
	if len(json.dumps(patch)) > cint(frappe.conf.get("docstudio_max_patch_bytes") or 2_000_000):
		frappe.throw(_("Too many changes in one request."))
