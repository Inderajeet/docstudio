// The "Preview & Edit" view that replaces the form body while open.

import { Renderer } from "./renderer";
import { InlineEditor } from "./editor";
import { FormatToolbar } from "./toolbar";
import { LayoutEditor } from "./layout";
import { PatchState } from "./state";
import { esc, debounce, ensure_web_fonts, PAGE_MM } from "./utils";

const SAVE_TO_FORM = "Save to Form";
const DOCUMENT_ONLY = "Save as Document Only";
const API = "docstudio.api";

export function iter_nodes(model) {
	const out = [];
	for (const s of model.sections) {
		switch (s.type) {
			case "letterhead":
				out.push(s.company.name, ...s.company.lines);
				break;
			case "title":
				out.push(s.heading);
				if (s.subtitle) out.push(s.subtitle);
				break;
			case "header":
				if (s.left) out.push(...s.left.items);
				out.push(...s.right.items);
				break;
			case "fields":
				s.columns.forEach((c) => out.push(...c));
				break;
			case "table":
				s.rows.forEach((r) => out.push(...r.cells));
				break;
			case "totals":
				out.push(...s.items);
				break;
			case "signature":
				out.push(...s.lines);
				break;
			default:
				if (s.node) out.push(s.node);
		}
	}
	return out.filter(Boolean);
}

export class Preview {
	constructor(frm) {
		this.frm = frm;
		this.doctype = frm.doctype;
		this.name = frm.doc.name;
		this.editor = new InlineEditor(this);
		this.format = new FormatToolbar(this);
		this.layout = new LayoutEditor(this);
		this.state = new PatchState({});
		this.template = null;
		this.theme = null;
		this.save_mode = null;
		this.model = null;
		this.nodes = {};
		this.busy = false;
		this.render_seq = 0;
		this.request_render = debounce(() => this.server_render(), 250);
		this.on_resize = debounce(() => this.fit_page(), 100);
	}

	is_open() {
		return !!this.$root;
	}

	async open() {
		if (this.frm.is_dirty()) {
			frappe.msgprint(__("Save your changes on the form before opening the preview."));
			return;
		}
		this.mount();
		this.set_loading(true, __("Loading preview..."));
		try {
			const r = await frappe.call({
				method: `${API}.get_preview`,
				args: { doctype: this.doctype, name: this.name },
			});
			this.load(r.message);
		} catch (e) {
			this.unmount();
			return;
		}
		this.set_loading(false);
	}

	load(data) {
		this.info = data;
		this.state.reset(data.patch);
		this.template = data.model.meta.template;
		this.theme = data.model.meta.theme;
		this.save_mode = data.model.meta.save_mode;
		this.render_toolbar();
		this.show_model(data.model);
		if (data.version) {
			this.set_status(
				__("Showing saved document version {0} ({1})", [
					data.version.version_no,
					frappe.datetime.str_to_user(data.version.creation),
				])
			);
		} else {
			this.set_status(this.can_edit_hint());
		}
	}

	mount() {
		const page = this.frm.page;
		this.$layout = page.wrapper.find(".layout-main").first();
		this.$layout.hide();
		page.page_actions.addClass("ds-hidden-by-docstudio").hide();
		// Inside the sticky page head (below the title row) so it is aligned identically on every DocType.
		const $head = page.wrapper.find(".page-head").first();
		const $head_container = $head.children(".container").first();
		this.$toolbar = $(`<div class="ds-toolbar ds-ui"></div>`).appendTo($head_container.length ? $head_container : $head);
		this.$root = $(`<div class="ds-root">
			<div class="ds-canvas"><div class="ds-page-wrap"></div></div>
			<div class="ds-loading"><div class="ds-spinner"></div><span></span></div>
		</div>`).insertAfter(this.$layout);
		this.$wrap = this.$root.find(".ds-page-wrap");
		this.editor.bind(this.$wrap);
		this.layout.bind(this.$wrap);
		this.bind_page_events();

		// Ctrl+S saves the document (Frappe's own primary action is hidden meanwhile).
		this._prev_save_action = frappe.container.page && frappe.container.page.save_action;
		if (frappe.container.page) frappe.container.page.save_action = () => this.save();
		$(window).on("resize.docstudio", this.on_resize);
		// Capture phase: Frappe's form has its own Ctrl+Z/Ctrl+Y undo that must not also fire.
		this._key_handler = (e) => this.on_key(e);
		window.addEventListener("keydown", this._key_handler, true);
		$(window).on("beforeunload.docstudio", (e) => {
			if (this.state.dirty) {
				e.preventDefault();
				return (e.returnValue = __("You have unsaved changes."));
			}
		});
		$("body").addClass("ds-preview-open");
	}

	unmount() {
		this.editor.finish_active(false);
		this.$root && this.$root.remove();
		this.$toolbar && this.$toolbar.remove();
		this.$root = this.$toolbar = null;
		this.$layout && this.$layout.show();
		this.frm.page.page_actions.removeClass("ds-hidden-by-docstudio").show();
		if (frappe.container.page) frappe.container.page.save_action = this._prev_save_action;
		$(window).off(".docstudio");
		window.removeEventListener("keydown", this._key_handler, true);
		$("body").removeClass("ds-preview-open");
	}

	close() {
		const done = () => {
			this.unmount();
			this.frm.refresh();
		};
		if (this.state.dirty) {
			frappe.confirm(__("You have unsaved changes in the document. Leave without saving?"), done);
		} else {
			done();
		}
	}

	on_form_refresh() {
		// Frappe re-shows its actions on every refresh; keep them hidden while we're open.
		this.frm.page.page_actions.hide();
	}

	can_edit_hint() {
		if (this.save_mode === DOCUMENT_ONLY) {
			return __("Click any underlined text to edit. Changes are kept with the document only.");
		}
		return __("Click any underlined value to edit it.");
	}

	render_toolbar() {
		const info = this.info;
		const opt = (v, label, sel) => `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(label)}</option>`;
		const templates =
			opt("", __("Auto Layout"), this.template || "") +
			info.templates.map((t) => opt(t.name, t.name, this.template)).join("");
		const themes = info.themes.map((t) => opt(t.name, t.name, this.theme)).join("");
		const layout = this.state.patch.layout || {};
		const terms_value = "terms_block" in layout ? layout.terms_block || "" : "__default__";
		const terms_select = (info.terms_blocks || []).length
			? `<select class="form-control input-xs ds-terms" title="${__("Terms block")}">
				${opt("__default__", __("Terms: template default"), terms_value)}
				${opt("", __("Terms: none"), terms_value)}
				${info.terms_blocks.map((b) => opt(b.name, b.title, terms_value)).join("")}
			</select>`
			: "";
		const mode_select = info.can_write
			? `<select class="form-control input-xs ds-mode" title="${__("What Save does")}">
				${opt(SAVE_TO_FORM, __("Save to Form"), this.save_mode)}
				${opt(DOCUMENT_ONLY, __("Save as Document Only"), this.save_mode)}
			</select>`
			: `<span class="ds-badge" title="${__("Submitted, cancelled or read-only records are never changed")}">${__(
					"Document only"
			  )}</span>`;

		this.$toolbar.html(`
			<div class="ds-tb-row">
				<div class="ds-tb-title">
					<span class="ds-tb-doc">${esc(__(this.doctype))} &middot; ${esc(this.name)}</span>
					<span class="ds-status text-muted"></span>
				</div>
				<div class="ds-tb-group">
					<select class="form-control input-xs ds-template" title="${__("Template")}">${templates}</select>
					<select class="form-control input-xs ds-theme" title="${__("Theme")}">${themes}</select>
					${terms_select}
					${mode_select}
				</div>
				<div class="ds-tb-group">
					<button class="btn btn-xs btn-default ds-undo" title="${__("Undo")} (Ctrl+Z)">&#8630;</button>
					<button class="btn btn-xs btn-default ds-redo" title="${__("Redo")} (Ctrl+Y)">&#8631;</button>
					<div class="btn-group">
						<button class="btn btn-xs btn-default dropdown-toggle" data-toggle="dropdown" aria-expanded="false">${__("Layout")} <span class="caret"></span></button>
						<ul class="dropdown-menu dropdown-menu-right">
							${info.is_admin ? `<li><a class="dropdown-item ds-layout-save">${__("Save layout to template")}</a></li>` : ""}
							<li><a class="dropdown-item ds-layout-reset">${__("Reset layout for this document")}</a></li>
						</ul>
					</div>
					<button class="btn btn-xs btn-default ds-back">${__("Back to Form")}</button>
					<div class="btn-group">
						<button class="btn btn-xs btn-default ds-download">${__("Download .docx")}</button>
						<button class="btn btn-xs btn-default dropdown-toggle" data-toggle="dropdown" aria-expanded="false"><span class="caret"></span></button>
						<ul class="dropdown-menu dropdown-menu-right">
							<li><a class="dropdown-item ds-attach">${__("Attach .docx to this record")}</a></li>
						</ul>
					</div>
					<button class="btn btn-xs btn-primary ds-save">${__("Save")}</button>
				</div>
			</div>
			<div class="ds-tb-row ds-tb-format"></div>`);

		const $t = this.$toolbar;
		$t.find(".ds-back").on("click", () => this.close());
		$t.find(".ds-save").on("click", () => this.save());
		$t.find(".ds-download").on("click", () => this.download());
		$t.find(".ds-attach").on("click", () => this.attach());
		$t.find(".ds-undo").on("click", () => this.undo());
		$t.find(".ds-layout-save").on("click", () => this.layout.save_to_template());
		$t.find(".ds-layout-reset").on("click", () => this.layout.reset());
		$t.find(".ds-redo").on("click", () => this.redo());
		$t.find(".ds-template").on("change", (e) => {
			this.template = e.target.value || null;
			this.theme = null; // let the template's theme apply
			this.server_render(true);
		});
		$t.find(".ds-theme").on("change", (e) => {
			this.theme = e.target.value;
			this.server_render(true);
		});
		$t.find(".ds-terms").on("change", (e) => {
			const layout = { ...(this.state.patch.layout || {}) };
			if (e.target.value === "__default__") delete layout.terms_block;
			else layout.terms_block = e.target.value;
			this.state.set_layout(layout);
			// A different block starts from its own text, not the previous block's edits.
			delete this.state.patch.overrides["terms:block"];
			this.after_structural_change();
		});
		$t.find(".ds-mode").on("change", (e) => {
			this.save_mode = e.target.value;
			this.server_render(true);
		});
		this.format.mount($t.find(".ds-tb-format"));
		this.update_buttons();
	}

	update_buttons() {
		if (!this.$toolbar) return;
		const dirty = this.state.dirty;
		this.$toolbar.find(".ds-save").prop("disabled", !dirty || this.busy);
		this.$toolbar.find(".ds-undo").prop("disabled", !this.state.undo_stack.length);
		this.$toolbar.find(".ds-redo").prop("disabled", !this.state.redo_stack.length);
		const $tpl = this.$toolbar.find(".ds-template");
		if (this.template && !$tpl.find(`option[value="${CSS.escape(this.template)}"]`).length) {
			$tpl.append($("<option>").val(this.template).text(this.template)); // created from this preview
		}
		$tpl.val(this.template || "");
		this.$toolbar.find(".ds-theme").val(this.theme || "");
		const layout = this.state.patch.layout || {};
		this.$toolbar.find(".ds-terms").val("terms_block" in layout ? layout.terms_block || "" : "__default__");
	}

	set_status(msg) {
		this.$toolbar && this.$toolbar.find(".ds-status").text(msg || "");
	}

	set_loading(on, msg = "") {
		if (!this.$root) return;
		this.$root.toggleClass("ds-is-loading", !!on);
		this.$root.find(".ds-loading span").text(msg);
	}

	show_model(model) {
		this.model = model;
		this.nodes = {};
		iter_nodes(model).forEach((n) => (this.nodes[n.id] = n));
		// Pseudo-nodes so whole columns / tables can be selected and formatted.
		for (const s of model.sections.filter((x) => x.type === "table")) {
			this.nodes[s.id] = { id: s.id, kind: "table", label: `${__("Table")}: ${s.label || __("Items")}`, style: {}, display: "" };
			for (const c of s.columns) {
				const id = `col:${s.id}:${c.field}`;
				this.nodes[id] = { id, kind: "column", label: `${__("Column")}: ${c.label}`, style: c.style || {}, display: "" };
			}
		}
		ensure_web_fonts(model.theme.font_family);
		const renderer = new Renderer({ changed: this.state.changed });
		this.$wrap.html(renderer.render(model));
		this.fit_page();
		this.update_buttons();
		if (this.format.selected && !this.nodes[this.format.selected]) this.format.selected = null;
		this.format.highlight();
		this.format.refresh();
		this.layout.after_render(this.$wrap.find(".ds-page"));
	}

	fit_page() {
		if (!this.$root || !this.model) return;
		// Scale the A4/Letter page down on narrow screens instead of reflowing it.
		const [w] = PAGE_MM[this.model.theme.page_size] || PAGE_MM.A4;
		const page_px = (w / 25.4) * 96;
		const available = this.$root.find(".ds-canvas").width() - 32;
		const zoom = available > 0 && available < page_px ? available / page_px : 1;
		this.$wrap.css("zoom", zoom);
	}

	async server_render(show_loading = false) {
		const seq = ++this.render_seq;
		if (show_loading) this.set_loading(true, __("Updating..."));
		try {
			const r = await frappe.call({
				method: `${API}.render`,
				type: "POST",
				args: this.request_args(),
			});
			if (seq === this.render_seq && this.$root) this.show_model(r.message.model);
		} finally {
			if (seq === this.render_seq) this.set_loading(false);
		}
	}

	request_args() {
		return {
			doctype: this.doctype,
			name: this.name,
			template: this.template || "",
			theme: this.theme || "",
			save_mode: this.save_mode || "",
			patch: JSON.stringify(this.state.patch),
		};
	}

	commit(node, value) {
		this.state.set_value(node, value);
		this.set_status(__("Unsaved changes"));
		this.update_buttons();
		// Optimistic local update, then the server recomputes formatting and totals.
		const $el = this.$wrap.find(`[data-id="${CSS.escape(node.id)}"]`);
		if (!node.html) $el.text(value).addClass("ds-changed").removeClass("ds-empty");
		else $el.addClass("ds-changed");
		this.request_render();
	}

	after_format() {
		// Styles are pure display: re-render locally right away; the server applies the same
		// patch.styles on the next render, save and export.
		this.set_status(__("Unsaved changes"));
		this.show_model(this.model);
	}

	bind_page_events() {
		const table_of = (el) => $(el).closest("table.ds-items").attr("data-table-sid") || null;
		this.$wrap.on("click", ".ds-node", (e) => {
			this.format.select($(e.currentTarget).attr("data-id"), table_of(e.currentTarget));
		});
		// A click anywhere in a cell (not just on its text) edits/selects that cell.
		this.$wrap.on("click", ".ds-items td", (e) => {
			if ($(e.target).closest(".ds-node, .ds-ui, .ds-editing").length) return;
			const $node = $(e.currentTarget).find(".ds-node").first();
			if ($node.length) $node.trigger("click");
		});
		this.$wrap.on("click", "th.ds-col-pick", (e) => {
			if ($(e.target).closest(".ds-ui").length) return;
			this.editor.finish_active(true);
			this.format.select($(e.currentTarget).attr("data-col"), table_of(e.currentTarget));
		});
		this.$wrap.on("click", "th.ds-table-pick", (e) => {
			this.editor.finish_active(true);
			const sid = table_of(e.currentTarget);
			this.format.select(sid, sid);
		});
		this.$wrap.on("click", ".ds-add-row", (e) => {
			this.editor.finish_active(true);
			this.state.add_row($(e.currentTarget).attr("data-table"));
			this.after_structural_change();
		});
		this.$wrap.on("click", ".ds-row-del", (e) => {
			e.stopPropagation();
			this.editor.finish_active(true);
			const $b = $(e.currentTarget);
			this.state.delete_row($b.attr("data-table"), $b.attr("data-row"));
			this.after_structural_change();
		});
	}

	after_structural_change() {
		this.set_status(__("Unsaved changes"));
		this.update_buttons();
		this.server_render(true);
	}

	undo() {
		if (this.editor.editing) return;
		if (this.state.undo()) this.after_structural_change();
	}

	redo() {
		if (this.editor.editing) return;
		if (this.state.redo()) this.after_structural_change();
	}

	on_key(e) {
		if (!this.$root || this.editor.editing) return;
		if ($(e.target).is("input, textarea, select, [contenteditable]")) return;
		const mod = e.ctrlKey || e.metaKey;
		const key = (e.key || "").toLowerCase();
		if (mod && !e.shiftKey && key === "z") {
			e.preventDefault();
			e.stopPropagation();
			this.undo();
		} else if (mod && (key === "y" || (e.shiftKey && key === "z"))) {
			e.preventDefault();
			e.stopPropagation();
			this.redo();
		}
	}

	async save() {
		this.editor.finish_active(true);
		// Let the blur-commit settle before reading the patch.
		await new Promise((r) => setTimeout(r, 20));
		if (!this.state.dirty || this.busy) return;
		this.busy = true;
		this.update_buttons();
		this.set_loading(true, __("Saving..."));
		try {
			const args = { ...this.request_args(), modified: this.model.meta.modified };
			const r = await frappe.call({ method: `${API}.save`, type: "POST", args });
			const res = r.message;
			if (res.mode === SAVE_TO_FORM && this.state.has_record_changes) {
				await this.frm.reload_doc();
				this.frm.page.page_actions.hide();
			}
			const fresh = await frappe.call({
				method: `${API}.get_preview`,
				args: { doctype: this.doctype, name: this.name, template: this.template || "", theme: this.theme || "", save_mode: this.save_mode },
			});
			this.load(fresh.message);
			frappe.show_alert({
				message:
					res.mode === SAVE_TO_FORM
						? __("Saved to {0}", [__(this.doctype)])
						: __("Saved as document version {0}", [res.version.version_no]),
				indicator: "green",
			});
		} finally {
			this.busy = false;
			this.set_loading(false);
			this.update_buttons();
		}
	}

	download() {
		this.editor.finish_active(true);
		setTimeout(() => {
			open_url_post(`/api/method/${API}.download_docx`, this.request_args());
			frappe.show_alert({ message: __("Preparing .docx..."), indicator: "blue" });
		}, 20);
	}

	async attach() {
		this.editor.finish_active(true);
		const r = await frappe.call({
			method: `${API}.attach_docx`,
			type: "POST",
			args: this.request_args(),
			freeze: true,
			freeze_message: __("Generating .docx..."),
		});
		frappe.show_alert({ message: __("Attached {0}", [r.message.split("/").pop()]), indicator: "green" });
		this.frm.reload_doc().then(() => this.frm.page.page_actions.hide());
	}
}
