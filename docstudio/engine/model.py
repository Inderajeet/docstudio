"""The DocModel: one JSON structure consumed by the HTML preview and the .docx writer."""

from frappe import _

from docstudio.engine.formatting import MULTILINE, NUMERIC, RICH, format_display, json_safe


def field_id(fieldname):
	return f"f:{fieldname}"


def cell_id(table, rowname, fieldname):
	return f"c:{table}:{rowname}:{fieldname}"


def text_node(node_id, display, editable=False, html=False, style=None, label=None):
	return {
		"id": node_id,
		"kind": "text",
		"label": label,
		"display": display or "",
		"html": html,
		"editable": editable,
		"writable": False,
		"style": style or {},
	}


def value_node(df, value, row=None, parent=None, table=None, editable=False, writable=False, label=None):
	ft = df.fieldtype
	node = {
		"id": cell_id(table, row.name, df.fieldname) if table else field_id(df.fieldname),
		"kind": "value",
		"bind": {"field": df.fieldname, "table": table, "row": row.name if table else None},
		"label": label if label is not None else _(df.label or df.fieldname),
		"fieldtype": ft,
		"options": df.options if ft in ("Link", "Select") else None,
		"value": json_safe(value),
		"display": format_display(value, df, row if table else parent, parent),
		"html": ft in RICH,
		"multiline": ft in MULTILINE,
		"align": "right" if ft in NUMERIC else None,
		"editable": editable,
		"writable": writable,
		"style": {},
	}
	return node


def section(section_id, section_type, label=None, **kw):
	s = {"id": section_id, "type": section_type, "label": label, "hidden": False}
	s.update(kw)
	return s


def iter_nodes(model):
	"""Yield every node in the model (for applying overrides and styles by id)."""
	for s in model.get("sections", []):
		yield from _section_nodes(s)


def _section_nodes(s):
	t = s["type"]
	if t == "letterhead":
		yield s["company"]["name"]
		yield from s["company"]["lines"]
	elif t == "title":
		yield s["heading"]
		if s.get("subtitle"):
			yield s["subtitle"]
	elif t == "header":
		if s.get("left"):
			yield from s["left"]["items"]
		yield from s["right"]["items"]
	elif t == "fields":
		for col in s["columns"]:
			yield from col
	elif t == "table":
		for r in s["rows"]:
			yield from r["cells"]
	elif t == "totals":
		yield from s["items"]
	elif t in ("rich_text", "terms", "text"):
		yield s["node"]
	elif t == "signature":
		yield from s["lines"]
