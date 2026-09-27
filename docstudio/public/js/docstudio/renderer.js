// DocModel -> HTML. Mirrors docstudio/export/docx_writer.py section by section.
// Everything with a `ds-ui` class is preview-only chrome and is never part of the document.
// Hidden sections/fields/columns are still drawn here (dimmed) so they can be shown again;
// the .docx writer omits them.

import { esc, text_html, style_css, font_stack, PAGE_MM } from "./utils";

const EYE = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>`;
const EYE_OFF = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 19c-7 0-11-7-11-7a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 7 11 7a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

// Same rules as DocxWriter.s_table() in docstudio/export/docx_writer.py.
function head_fill(t) {
	return t.table_style === "Minimal" ? "transparent" : t.header_shading;
}

export class Renderer {
	constructor({ changed = new Set(), tools = true } = {}) {
		this.changed = changed; // node ids edited since the last save
		this.tools = tools; // section/field visibility controls
	}

	page_vars(theme) {
		const [w, h] = PAGE_MM[theme.page_size] || PAGE_MM.A4;
		return [
			`--ds-font:${font_stack(theme.font_family)}`,
			`--ds-size:${theme.base_font_size}pt`,
			`--ds-heading:${theme.heading_font_size}pt`,
			`--ds-line:${theme.line_spacing}`,
			`--ds-primary:${theme.primary_color}`,
			`--ds-text:${theme.text_color}`,
			`--ds-shade:${theme.header_shading}`,
			`--ds-border:${theme.border_color}`,
			`--ds-head-fill:${head_fill(theme)}`,
			`--ds-page-w:${w}mm`,
			`--ds-page-h:${h}mm`,
			`padding:${theme.margin_top}mm ${theme.margin_right}mm ${theme.margin_bottom}mm ${theme.margin_left}mm`,
		].join(";");
	}

	render(model) {
		const t = model.theme;
		this.model = model;
		const sections = model.sections.map((s) => this.section(s, t)).join("");
		return `<div class="ds-page ds-table-${(t.table_style || "Bordered").toLowerCase()}" style="${esc(
			this.page_vars(t)
		)}">${sections}</div>`;
	}

	// ── nodes ──────────────────────────────────────────────
	node(n, { extra_style = null, block = false, tag = null } = {}) {
		if (!n) return "";
		const style = { ...(extra_style || {}), ...(n.style || {}) };
		const cls = ["ds-node"];
		if (n.editable) cls.push("ds-ed");
		if (n.hidden) cls.push("ds-node-hidden");
		if (this.changed.has(n.id)) cls.push("ds-changed");
		const empty = !String(n.display || "").trim();
		if (empty && n.editable) cls.push("ds-empty");
		const content = n.html ? n.display || "" : text_html(n.display);
		const el = tag || (n.html || block ? "div" : "span");
		return `<${el} class="${cls.join(" ")}" data-id="${esc(n.id)}" style="${esc(
			style_css(style, { block: el === "div" })
		)}">${content}</${el}>`;
	}

	eye(kind, id, hidden) {
		if (!this.tools) return "";
		return `<button class="ds-ui ds-eye" data-kind="${kind}" data-target="${esc(id)}" title="${
			hidden ? __("Show in document") : __("Hide from document")
		}">${hidden ? EYE_OFF : EYE}</button>`;
	}

	label(s) {
		return s.label ? `<div class="ds-sec-label">${esc(s.label)}</div>` : "";
	}

	section(s, theme) {
		const fn = this[`s_${s.type}`];
		if (!fn) return "";
		const inner = fn.call(this, s, theme);
		if (!inner) return "";
		const cls = ["ds-sec", `ds-sec-${s.type}`];
		if (s.hidden) cls.push("ds-sec-hidden");
		const page_break = s.style && s.style.page_break_before;
		const marker = page_break ? `<div class="ds-ui ds-page-break-marker"><span>${__("Page break")}</span></div>` : "";
		const tools = this.tools
			? `<div class="ds-ui ds-sec-tools">
				<span class="ds-sec-handle" title="${__("Drag to move this section")}">&#8942;&#8942;</span>
				${this.eye("section", s.id, s.hidden)}
				<button class="ds-ui ds-pb ${page_break ? "active" : ""}" data-target="${esc(s.id)}" title="${__(
					"Start this section on a new page"
			  )}">&#8615;</button>
			</div>`
			: "";
		return `<section class="${cls.join(" ")}" data-sid="${esc(s.id)}">${marker}${tools}${inner}</section>`;
	}

	kv(nodes, cls = "") {
		const rows = nodes
			.map(
				(n) =>
					`<tr class="${n.hidden ? "ds-row-hidden" : ""}"><td class="ds-kv-label">${this.eye("node", n.id, n.hidden)}${esc(
						n.label || ""
					)}</td><td class="ds-kv-value">${this.node(n)}</td></tr>`
			)
			.join("");
		return rows ? `<table class="ds-kv ${cls}">${rows}</table>` : "";
	}

	// ── sections ───────────────────────────────────────────
	s_letterhead(s) {
		const c = s.company;
		const lines = c.lines.map((n) => this.node(n, { block: true })).join("");
		const logo = c.logo ? `<div class="ds-lh-logo"><img src="${esc(c.logo)}" alt=""></div>` : "";
		return `<div class="ds-letterhead">
			<div class="ds-lh-text">
				${this.node(c.name, { block: true })}
				<div class="ds-lh-lines">${lines}</div>
			</div>${logo}
		</div><div class="ds-rule"></div>`;
	}

	s_title(s, theme) {
		const align = (s.heading.style && s.heading.style.align) || (theme.heading_align || "Center").toLowerCase();
		const sub = s.subtitle ? `<div class="ds-subtitle">${this.node(s.subtitle)}</div>` : "";
		return `<div class="ds-title" style="text-align:${align}">${this.node(s.heading)}${sub}</div>`;
	}

	s_header(s) {
		const left_items = (s.left && s.left.items) || [];
		const has_left = left_items.some((n) => !n.hidden) || (this.tools && left_items.length);
		const item = (n) => {
			const eye = this.eye("node", n.id, n.hidden);
			return n.label
				? `<div class="${n.hidden ? "ds-row-hidden" : ""}">${eye}<span class="ds-inline-label">${esc(
						n.label
				  )}:</span> ${this.node(n)}</div>`
				: `<div class="ds-inline-item ${n.hidden ? "ds-row-hidden" : ""}">${eye}${this.node(n, { block: true })}</div>`;
		};
		const to = has_left
			? `<div class="ds-box ds-to"><div class="ds-box-title">${esc(s.left.title)}</div>${left_items
					.map(item)
					.join("")}</div>`
			: `<div class="ds-box ds-box-empty"></div>`;
		return `<div class="ds-header ${has_left ? "" : "ds-header-right-only"}">${to}<div class="ds-box ds-meta">${this.kv(
			s.right.items
		)}</div></div>`;
	}

	s_fields(s) {
		const cols = s.columns.filter((c) => c.length);
		if (!cols.length) return "";
		if (cols.length === 1) return this.label(s) + this.kv(cols[0], "ds-kv-wide");
		const boxes = cols.map((c) => `<div class="ds-box">${this.kv(c)}</div>`).join("");
		return `${this.label(s)}<div class="ds-cols ${s.boxed === false ? "" : "ds-boxed"}" style="grid-template-columns:repeat(${
			cols.length
		},1fr)">${boxes}</div>`;
	}

	s_table(s, theme) {
		const cols = s.columns.map((c, i) => [c, i]);
		const cls = (c) => [c.align === "right" ? "ds-num" : "", c.hidden ? "ds-col-hidden" : ""].join(" ");
		// Per-table style chosen in the preview overrides the theme (mirrors DocxWriter.s_table).
		const tt = { ...theme, table_style: (s.table_style || {}).table_style || theme.table_style };
		const vars = `--ds-head-fill:${head_fill(tt)}`;
		const head = `<tr><th class="ds-sno ds-table-pick" title="${__("Select the whole table")}">${__("S.No")}</th>${cols
			.map(
				([c]) =>
					`<th class="${cls(c)} ds-col-pick" data-col="col:${esc(s.id)}:${esc(c.field)}" style="${esc(
						style_css(c.style || {}, { block: true })
					)}">${this.eye("column", `${s.id}:${c.field}`, c.hidden)}${esc(c.label)}</th>`
			)
			.join("")}</tr>`;
		const body = s.rows
			.map((r, n) => {
				const del = s.can_edit_rows
					? `<button class="ds-ui ds-row-del" data-table="${esc(s.table)}" data-row="${esc(r.name)}" title="${__(
							"Remove row"
					  )}">&times;</button>`
					: "";
				const cells = cols.map(([c, i]) => `<td class="${cls(c)}">${this.node(r.cells[i])}</td>`).join("");
				return `<tr data-row="${esc(r.name)}"><td class="ds-sno">${del}${n + 1}</td>${cells}</tr>`;
			})
			.join("");
		const empty = s.rows.length
			? ""
			: `<tr class="ds-ui"><td colspan="${cols.length + 1}" class="ds-empty-table">${__(
					"No rows. Rows you add here are included in the document."
			  )}</td></tr>`;
		const add = s.can_edit_rows
			? `<button class="ds-ui btn btn-xs btn-default ds-add-row" data-table="${esc(s.table)}">+ ${__("Add Row")}</button>`
			: "";
		return `${this.label(s)}<table class="ds-items ds-ts-${(tt.table_style || "Bordered").toLowerCase()}" data-table-sid="${esc(
			s.id
		)}" style="${esc(vars)}"><thead>${head}</thead><tbody>${body}${empty}</tbody></table>${add}`;
	}

	s_totals(s, theme) {
		const rows = s.items
			.map(
				(n) =>
					`<tr class="${[n.grand ? "ds-grand" : "", n.hidden ? "ds-row-hidden" : ""].join(
						" "
					)}"><td class="ds-num">${this.eye("node", n.id, n.hidden)}${esc(n.label)}</td><td class="ds-num">${this.node(
						n
					)}</td></tr>`
			)
			.join("");
		return rows
			? `<table class="ds-totals ds-ts-${(theme.table_style || "Bordered").toLowerCase()}">${rows}</table>`
			: "";
	}

	s_rich_text(s) {
		return `${this.label(s)}<div class="ds-rich">${this.node(s.node, { block: true })}</div>`;
	}

	s_terms(s) {
		return this.s_rich_text(s);
	}

	s_text(s) {
		return this.s_rich_text(s);
	}

	s_signature(s) {
		const lines = s.lines;
		return `<div class="ds-signature">${lines
			.map(
				(n, i) =>
					`<div class="${i === lines.length - 1 && lines.length > 1 ? "ds-sign-line" : ""}">${this.node(n)}</div>`
			)
			.join("")}</div>`;
	}
}
