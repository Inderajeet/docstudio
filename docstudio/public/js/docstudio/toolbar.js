// Formatting toolbar: size, bold, italic, underline, alignment, color.
//
// Formatting is stored per node in patch.styles (so it reaches the .docx through the model).
// While a rich-text block is being edited and text is selected inside it, bold/italic/
// underline/color apply inline to that selection instead (kept in the block's HTML).

import { esc } from "./utils";

const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28];
const INLINE = { bold: "bold", italic: "italic", underline: "underline" };

export class FormatToolbar {
	constructor(preview) {
		this.preview = preview;
		this.selected = null; // node id
	}

	mount($row) {
		this.$row = $row;
		const btn = (cmd, label, title) =>
			`<button class="btn btn-xs btn-default ds-fmt-btn" data-cmd="${cmd}" title="${esc(title)}">${label}</button>`;
		const sizes = SIZES.map((s) => `<option value="${s}">${s} pt</option>`).join("");
		$row.html(`
			<span class="ds-fmt-target text-muted small">${__("Click text in the document to format it")}</span>
			<div class="ds-tb-group ds-fmt-controls">
				<select class="form-control input-xs ds-fmt-size" title="${__("Font size")}">
					<option value="">${__("Size")}</option>${sizes}
				</select>
				${btn("bold", "<b>B</b>", __("Bold"))}
				${btn("italic", "<i>I</i>", __("Italic"))}
				${btn("underline", "<u>U</u>", __("Underline"))}
				<span class="ds-tb-sep"></span>
				${btn("align:left", "&#8676;", __("Align left"))}
				${btn("align:center", "&#8596;", __("Center"))}
				${btn("align:right", "&#8677;", __("Align right"))}
				${btn("align:justify", "&#8801;", __("Justify"))}
				<span class="ds-tb-sep"></span>
				<input type="color" class="ds-fmt-color" title="${__("Text color")}" value="#222222">
				${btn("clear", "&#10005;", __("Clear formatting"))}
			</div>
			<div class="ds-tb-group ds-fmt-table" style="display:none">
				<span class="ds-tb-sep"></span>
				<span class="small text-muted">${__("Table")}</span>
				<select class="form-control input-xs ds-tbl-style" title="${__("Table style")}"></select>
			</div>`);
		$row.find(".ds-tbl-style").on("change", (e) => this.table_style({ table_style: e.target.value }));

		// mousedown + preventDefault keeps focus (and the text selection) in the editor.
		$row.on("mousedown", ".ds-fmt-btn", (e) => {
			e.preventDefault();
			const cmd = $(e.currentTarget).attr("data-cmd");
			if (cmd === "clear") this.clear();
			else if (cmd.startsWith("align:")) this.apply({ align: cmd.split(":")[1] }, "align");
			else this.toggle(cmd);
		});
		$row.find(".ds-fmt-size").on("change", (e) => {
			const size = e.target.value ? Number(e.target.value) : null;
			this.apply({ size }, "size");
		});
		$row.find(".ds-fmt-controls .ds-fmt-color").on("input change", (e) => {
			if (e.type === "input" && this.inline_selection()) return; // apply once, on change
			this.color(e.target.value);
		});
		this.refresh();
	}

	node() {
		return this.selected ? this.preview.nodes[this.selected] : null;
	}

	select(id, table_sid = null) {
		this.selected = id;
		this.table_sid = table_sid;
		this.highlight();
		this.refresh();
	}

	table_section() {
		return this.table_sid && this.preview.model
			? this.preview.model.sections.find((s) => s.id === this.table_sid)
			: null;
	}

	refresh_table_controls() {
		const $g = this.$row.find(".ds-fmt-table");
		const section = this.table_section();
		$g.toggle(!!section);
		if (!section) return;
		const style = (section.table_style || {}).table_style || this.preview.model.theme.table_style;
		$g.find(".ds-tbl-style").html(
			["Bordered", "Minimal"]
				.map((v) => `<option value="${v}" ${v === style ? "selected" : ""}>${__(v)}</option>`)
				.join("")
		);
	}

	table_style(style) {
		if (!this.table_sid) return;
		this.preview.editor.finish_active(true);
		this.preview.state.set_style(this.table_sid, style);
		// The server validates the style and redraws the table.
		this.preview.after_structural_change();
	}

	highlight() {
		const $wrap = this.preview.$wrap;
		if (!$wrap) return;
		$wrap.find(".ds-selected").removeClass("ds-selected");
		if (!this.selected) return;
		const sel = CSS.escape(this.selected);
		const node = this.node();
		if (node && node.kind === "column") {
			$wrap.find(`th[data-col="${sel}"]`).addClass("ds-selected");
		} else if (node && node.kind === "table") {
			$wrap.find(`table[data-table-sid="${sel}"]`).addClass("ds-selected");
		} else {
			$wrap.find(`[data-id="${sel}"]`).addClass("ds-selected");
		}
	}

	refresh() {
		if (!this.$row) return;
		this.refresh_table_controls();
		const node = this.node();
		const style = (node && node.style) || {};
		this.$row.find(".ds-fmt-controls button, .ds-fmt-controls select, .ds-fmt-controls input").prop("disabled", !node);
		this.$row
			.find(".ds-fmt-target")
			.text(node ? __("Formatting: {0}", [node.label || this.describe(node)]) : __("Click text in the document to format it"));
		for (const cmd of Object.keys(INLINE)) {
			this.$row.find(`[data-cmd="${cmd}"]`).toggleClass("active", !!style[cmd]);
		}
		this.$row.find("[data-cmd^='align:']").removeClass("active");
		if (style.align) this.$row.find(`[data-cmd="align:${style.align}"]`).addClass("active");
		this.$row.find(".ds-fmt-size").val(style.size ? String(style.size) : "");
		const theme = this.preview.model && this.preview.model.theme;
		this.$row.find(".ds-fmt-controls .ds-fmt-color").val(style.color || (theme && theme.text_color) || "#222222");
	}

	describe(node) {
		const text = String(node.display || "").replace(/<[^>]+>/g, "").trim();
		return text.length > 30 ? text.slice(0, 30) + "..." : text;
	}

	// A non-empty text selection inside the rich-text block being edited.
	inline_selection() {
		const node = this.node();
		if (!node || !node.html || !this.preview.editor.editing) return false;
		const sel = window.getSelection();
		if (!sel || sel.isCollapsed || !sel.rangeCount) return false;
		const el = this.preview.$wrap.find(`[data-id="${CSS.escape(node.id)}"]`)[0];
		return !!el && el.contains(sel.anchorNode) && el.contains(sel.focusNode);
	}

	toggle(cmd) {
		if (this.inline_selection()) {
			document.execCommand("styleWithCSS", false, false);
			document.execCommand(INLINE[cmd]);
			return;
		}
		const node = this.node();
		if (!node) return;
		this.apply({ [cmd]: !(node.style && node.style[cmd]) }, cmd);
	}

	color(value) {
		if (this.inline_selection()) {
			document.execCommand("styleWithCSS", false, true);
			document.execCommand("foreColor", false, value);
			document.execCommand("styleWithCSS", false, false);
			return;
		}
		this.apply({ color: value }, "color");
	}

	apply(style) {
		const node = this.node();
		if (!node) return;
		this.preview.editor.finish_active(true);
		this.preview.state.set_style(node.id, style);
		node.style = { ...(node.style || {}), ...style };
		for (const k of Object.keys(node.style)) if (node.style[k] === null) delete node.style[k];
		if (node.kind === "column" || node.kind === "table") this.preview.after_structural_change();
		else this.preview.after_format();
	}

	clear() {
		const node = this.node();
		if (!node) return;
		this.preview.editor.finish_active(true);
		// Remove the overrides; the server re-applies the layout's own emphasis (e.g. bold totals).
		this.preview.state.set_style(node.id, { bold: null, italic: null, underline: null, size: null, color: null, align: null });
		this.preview.after_structural_change();
	}
}
