"""Resolve the theme for a render: explicit > template > settings default > built-in fallback."""

import frappe
from frappe.utils import cint, flt

DEFAULT_THEME = {
	"name": None,
	"is_standard": 0,
	"font_family": "Arial",
	"base_font_size": 10,
	"heading_font_size": 16,
	"line_spacing": 1.15,
	"primary_color": "#1F3864",
	"text_color": "#222222",
	"heading_align": "Center",
	"table_style": "Bordered",
	"header_shading": "#D9E2F3",
	"border_color": "#9E9E9E",
	"page_size": "A4",
	"margin_top": 18.0,
	"margin_bottom": 18.0,
	"margin_left": 18.0,
	"margin_right": 18.0,
}

PAGE_SIZES_MM = {"A4": (210, 297), "Letter": (215.9, 279.4)}
TABLE_STYLES = ("Bordered", "Minimal")


def theme_to_dict(theme_doc):
	out = dict(DEFAULT_THEME)
	out["name"] = theme_doc.name
	for key, default in DEFAULT_THEME.items():
		if key == "name":
			continue
		value = theme_doc.get(key)
		if value in (None, ""):
			continue
		if isinstance(default, int) and not isinstance(default, bool):
			value = cint(value) or default
		elif isinstance(default, float):
			value = flt(value) or default
		out[key] = value
	return out


def resolve_theme(theme_name=None, template=None):
	from docstudio.engine.access import get_settings

	for candidate in (
		theme_name,
		template.theme if template else None,
		get_settings().default_theme,
		"Business",
	):
		if candidate and frappe.db.exists("DocStudio Theme", candidate):
			return theme_to_dict(frappe.get_cached_doc("DocStudio Theme", candidate))
	return dict(DEFAULT_THEME)
