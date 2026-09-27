// Copyright (c) 2026, Inderajeet and contributors
// For license information, please see license.txt

frappe.ui.form.on("DocStudio Settings", {
	sync_standard_templates(frm) {
		frappe.call({
			method: "docstudio.install.sync_standard_templates",
			freeze: true,
			freeze_message: __("Syncing standard themes and templates..."),
			callback(r) {
				const templates = r.message.templates || [];
				frappe.msgprint({
					title: __("Standard Templates Synced"),
					indicator: "green",
					message: templates.length
						? __("Themes: {0}. Templates: {1}", [r.message.themes, templates.join(", ")])
						: __("Themes: {0}. No built-in templates apply to the DocTypes on this site.", [r.message.themes]),
				});
				frm.reload_doc();
			},
		});
	},
});
