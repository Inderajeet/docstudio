// Adds "Preview & Edit" to every eligible form without per-DocType code.

import { Preview } from "./preview";

frappe.provide("docstudio");

const registered = new Set();

docstudio.is_available = function (frm) {
	const boot = frappe.boot.docstudio;
	if (!boot || !boot.enabled || !boot.allowed) return false;
	const meta = frm.meta || {};
	if (meta.istable || meta.issingle || meta.is_virtual || meta.module === "DocStudio") return false;
	if ((boot.excluded || []).includes(frm.doctype)) return false;
	return !frm.is_new() && !frm.doc.__islocal;
};

docstudio.setup_form = function (frm) {
	const preview = frm.__docstudio;
	if (preview && preview.is_open()) {
		if (preview.name !== frm.doc.name) {
			// Navigated to another record of the same DocType while the preview was open.
			preview.unmount();
		} else {
			preview.on_form_refresh();
			return;
		}
	}
	if (!docstudio.is_available(frm)) return;
	frm.add_custom_button(__("Preview & Edit"), () => docstudio.open_preview(frm));
};

docstudio.open_preview = function (frm) {
	frm.__docstudio = new Preview(frm);
	return frm.__docstudio.open();
};

// A refresh handler registered at form-load runs after the DocType's own refresh handlers,
// so the button survives scripts that call frm.clear_custom_buttons().
$(document).on("form-load", (e, frm) => {
	if (registered.has(frm.doctype)) return;
	registered.add(frm.doctype);
	frappe.ui.form.on(frm.doctype, { refresh: (f) => docstudio.setup_form(f) });
});
