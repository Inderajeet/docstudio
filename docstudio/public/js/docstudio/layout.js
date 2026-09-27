// Section order, visibility (sections, fields, table columns) and page breaks.
// Changes go into patch.layout (this document only); admins can store them on the template.

const LIST_KEYS = {
	section: ["hidden", "shown"],
	node: ["hidden_nodes", "shown_nodes"],
	column: ["hidden_columns", "shown_columns"],
};
const LAYOUT_KEYS = ["order", "hidden", "shown", "hidden_nodes", "shown_nodes", "hidden_columns", "shown_columns", "page_breaks"];

export class LayoutEditor {
	constructor(preview) {
		this.preview = preview;
		this.sortable = null;
	}

	bind($wrap) {
		$wrap.on("click", ".ds-eye", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const $b = $(e.currentTarget);
			this.toggle_visibility($b.attr("data-kind"), $b.attr("data-target"));
		});
		$wrap.on("click", ".ds-pb", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this.toggle_page_break($(e.currentTarget).attr("data-target"));
		});
	}

	after_render($page) {
		if (this.sortable) this.sortable.destroy();
		this.sortable = null;
		if (!window.Sortable || !$page.length) return;
		this.sortable = window.Sortable.create($page[0], {
			draggable: "section.ds-sec",
			handle: ".ds-sec-handle",
			animation: 150,
			ghostClass: "ds-sec-ghost",
			// Mouse-event dragging behaves the same in every browser (and inside Frappe's page).
			forceFallback: true,
			fallbackTolerance: 3,
			onEnd: (evt) => {
				if (evt.oldIndex === evt.newIndex) return;
				const order = $page
					.children("section.ds-sec")
					.map((i, el) => el.getAttribute("data-sid"))
					.get();
				this.update((layout) => (layout.order = order));
			},
		});
	}

	current_hidden(kind, id) {
		const model = this.preview.model;
		if (kind === "section") return !!(model.sections.find((s) => s.id === id) || {}).hidden;
		if (kind === "node") return !!(this.preview.nodes[id] || {}).hidden;
		const [sid, field] = [id.slice(0, id.lastIndexOf(":")), id.slice(id.lastIndexOf(":") + 1)];
		const s = model.sections.find((x) => x.id === sid);
		return !!(s && (s.columns || []).find((c) => c.field === field) || {}).hidden;
	}

	toggle_visibility(kind, id) {
		const [hide_key, show_key] = LIST_KEYS[kind];
		const hidden = this.current_hidden(kind, id);
		this.update((layout) => {
			const hide = new Set(layout[hide_key] || []);
			const show = new Set(layout[show_key] || []);
			if (hidden) {
				hide.delete(id);
				show.add(id); // also overrides a template-level hide
			} else {
				show.delete(id);
				hide.add(id);
			}
			layout[hide_key] = [...hide];
			layout[show_key] = [...show];
		});
	}

	toggle_page_break(id) {
		this.update((layout) => {
			const breaks = new Set(layout.page_breaks || []);
			breaks.has(id) ? breaks.delete(id) : breaks.add(id);
			layout.page_breaks = [...breaks];
		});
	}

	update(fn) {
		const layout = JSON.parse(JSON.stringify(this.preview.state.patch.layout || {}));
		fn(layout);
		for (const k of LAYOUT_KEYS) if (Array.isArray(layout[k]) && !layout[k].length) delete layout[k];
		this.preview.state.set_layout(layout);
		this.preview.after_structural_change();
	}

	has_layout_changes() {
		const layout = this.preview.state.patch.layout || {};
		return LAYOUT_KEYS.some((k) => (layout[k] || []).length);
	}

	reset() {
		this.update((layout) => LAYOUT_KEYS.forEach((k) => delete layout[k]));
	}

	async save_to_template() {
		const p = this.preview;
		const layout = p.state.patch.layout || {};
		const template_label = p.template || __("a new default template for {0}", [__(p.doctype)]);
		frappe.confirm(
			__("Use this section order and visibility for all future {0} documents ({1})?", [__(p.doctype), template_label]),
			async () => {
				const r = await frappe.call({
					method: "docstudio.api.save_layout_to_template",
					type: "POST",
					args: { doctype: p.doctype, template: p.template || "", layout: JSON.stringify(layout) },
				});
				p.template = r.message;
				// The template now carries the layout; keep only document-specific choices.
				this.update((l) => LAYOUT_KEYS.forEach((k) => delete l[k]));
				frappe.show_alert({ message: __("Layout saved to template {0}", [r.message]), indicator: "green" });
			}
		);
	}
}
