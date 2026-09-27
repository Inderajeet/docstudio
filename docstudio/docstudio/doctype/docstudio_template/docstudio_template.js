// Copyright (c) 2026, Inderajeet and contributors
// For license information, please see license.txt

const DS_HIGHLIGHT_FIELDS = ["title_field", "party_field", "date_field", "total_field", "company_field"];

frappe.ui.form.on("DocStudio Template", {
	refresh(frm) {
		frm.trigger("set_highlight_options");
		if (frm.doc.is_standard) {
			frm.set_intro(__("This is a standard template shipped with DocStudio. You can change its theme, highlight fields and field mapping; duplicate it for bigger changes."));
		}
	},
	reference_doctype(frm) {
		DS_HIGHLIGHT_FIELDS.forEach((f) => frm.set_value(f, ""));
		frm.trigger("set_highlight_options");
	},
	set_highlight_options(frm) {
		if (!frm.doc.reference_doctype) return;
		frappe.call({
			method: "docstudio.docstudio.doctype.docstudio_template.docstudio_template.get_field_options",
			args: { doctype: frm.doc.reference_doctype },
			callback(r) {
				const options = [{ value: "", label: __("(Automatic)") }].concat(r.message || []);
				DS_HIGHLIGHT_FIELDS.forEach((f) => frm.set_df_property(f, "options", options));
			},
		});
	},
});
