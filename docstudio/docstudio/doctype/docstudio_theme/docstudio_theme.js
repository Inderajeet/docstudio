// Copyright (c) 2026, Inderajeet and contributors
// For license information, please see license.txt

frappe.ui.form.on("DocStudio Theme", {
	refresh(frm) {
		if (frm.doc.is_standard) {
			frm.set_intro(__("Standard themes can't be edited. Use Menu > Duplicate to make your own."));
		}
	},
});
