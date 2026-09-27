// The edits patch (see docstudio/engine/patch.py) plus session undo/redo.

import { clone } from "./utils";

const KEYS = {
	fields: {},
	rows: {},
	added_rows: {},
	deleted_rows: {},
	overrides: {},
	styles: {},
	layout: {},
};
const RECORD_KEYS = ["fields", "rows", "added_rows", "deleted_rows"];
const MAX_HISTORY = 200;

export function normalize(patch) {
	const out = {};
	for (const [k, v] of Object.entries(KEYS)) {
		const cur = patch && patch[k];
		out[k] = cur && typeof cur === "object" && !Array.isArray(cur) ? clone(cur) : clone(v);
	}
	return out;
}

export class PatchState {
	constructor(patch) {
		this.reset(patch);
	}

	reset(patch) {
		this.patch = normalize(patch);
		this.saved = JSON.stringify(this.patch);
		this.undo_stack = [];
		this.redo_stack = [];
		this.changed = new Set();
	}

	get dirty() {
		return JSON.stringify(this.patch) !== this.saved;
	}

	get has_record_changes() {
		return RECORD_KEYS.some((k) => Object.keys(this.patch[k]).length);
	}

	_current() {
		return JSON.stringify({ p: this.patch, c: [...this.changed] });
	}

	_restore(json) {
		const s = JSON.parse(json);
		this.patch = s.p;
		this.changed = new Set(s.c);
	}

	snapshot() {
		this.undo_stack.push(this._current());
		if (this.undo_stack.length > MAX_HISTORY) this.undo_stack.shift();
		this.redo_stack = [];
	}

	undo() {
		if (!this.undo_stack.length) return false;
		this.redo_stack.push(this._current());
		this._restore(this.undo_stack.pop());
		return true;
	}

	redo() {
		if (!this.redo_stack.length) return false;
		this.undo_stack.push(this._current());
		this._restore(this.redo_stack.pop());
		return true;
	}

	// ── edits ──────────────────────────────────────────────
	set_value(node, value) {
		this.snapshot();
		if (node.writable) {
			this._set_typed(node.bind, value);
		} else {
			this.patch.overrides[node.id] = value;
		}
		this.changed.add(node.id);
	}

	_set_typed(bind, value) {
		const p = this.patch;
		if (!bind.table) {
			p.fields[bind.field] = value;
			return;
		}
		if (String(bind.row).startsWith("new-")) {
			const row = (p.added_rows[bind.table] || []).find((r) => r.name === bind.row);
			if (row) row[bind.field] = value;
			return;
		}
		p.rows[bind.table] = p.rows[bind.table] || {};
		p.rows[bind.table][bind.row] = p.rows[bind.table][bind.row] || {};
		p.rows[bind.table][bind.row][bind.field] = value;
	}

	add_row(table) {
		this.snapshot();
		const rows = (this.patch.added_rows[table] = this.patch.added_rows[table] || []);
		const name = `new-${Date.now().toString(36)}${rows.length}`;
		rows.push({ name });
		return name;
	}

	delete_row(table, rowname) {
		this.snapshot();
		const p = this.patch;
		if (String(rowname).startsWith("new-")) {
			p.added_rows[table] = (p.added_rows[table] || []).filter((r) => r.name !== rowname);
			if (!p.added_rows[table].length) delete p.added_rows[table];
			return;
		}
		p.deleted_rows[table] = p.deleted_rows[table] || [];
		if (!p.deleted_rows[table].includes(rowname)) p.deleted_rows[table].push(rowname);
		if (p.rows[table]) delete p.rows[table][rowname];
	}

	set_style(id, style) {
		this.snapshot();
		const cur = { ...(this.patch.styles[id] || {}), ...style };
		for (const k of Object.keys(cur)) if (cur[k] === null || cur[k] === undefined) delete cur[k];
		if (Object.keys(cur).length) this.patch.styles[id] = cur;
		else delete this.patch.styles[id];
		this.changed.add(id);
	}

	set_layout(layout) {
		this.snapshot();
		this.patch.layout = layout;
	}
}
