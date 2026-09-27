// Click-to-edit for nodes marked `ds-ed`. Typed fields use Frappe controls (Link autocomplete,
// date picker, select); everything else is edited in place as plain text or rich text.

const CONTROL_TYPES = new Set(["Link", "Date", "Datetime", "Time", "Select", "Check"]);
const NUMERIC = new Set(["Currency", "Float", "Int", "Long Int", "Percent"]);
const POPUPS = ".datepicker, .awesomplete, .ds-toolbar";

export class InlineEditor {
	constructor(preview) {
		this.preview = preview;
		this.active = null; // {finish(commit)}
	}

	bind($page) {
		$page.on("click", ".ds-ed", (e) => {
			if (this.active) return;
			e.preventDefault();
			e.stopPropagation();
			this.start($(e.currentTarget));
		});
	}

	get editing() {
		return !!this.active;
	}

	finish_active(commit = true) {
		if (this.active) this.active.finish(commit);
	}

	start($el) {
		const node = this.preview.nodes[$el.attr("data-id")];
		if (!node || !node.editable) return;
		if (node.html) return this.start_rich($el, node);
		if (node.writable && CONTROL_TYPES.has(node.fieldtype)) return this.start_control($el, node);
		return this.start_plain($el, node);
	}

	_activate(finish) {
		let done = false;
		this.active = {
			finish: (commit) => {
				if (done) return;
				done = true;
				this.active = null;
				$(document).off("mousedown.ds-edit");
				finish(commit);
			},
		};
		return this.active;
	}

	_outside_click($el, active) {
		// Deferred so the click that opened the editor doesn't close it.
		setTimeout(() => {
			$(document).on("mousedown.ds-edit", (e) => {
				if ($el[0].contains(e.target) || $(e.target).closest(POPUPS).length) return;
				active.finish(true);
			});
		});
	}

	start_plain($el, node) {
		const el = $el[0];
		const original = el.innerHTML;
		const numeric = node.writable && NUMERIC.has(node.fieldtype);
		const raw = node.writable ? node.value ?? "" : node.display ?? "";
		const multiline = node.multiline || String(raw).includes("\n");

		$el.addClass("ds-editing").removeClass("ds-empty");
		el.innerText = raw;
		el.setAttribute("contenteditable", "true");
		el.focus();
		document.getSelection().selectAllChildren(el);

		const active = this._activate((commit) => {
			el.removeAttribute("contenteditable");
			$el.removeClass("ds-editing").off(".ds-edit");
			const text = el.innerText.replace(/\n$/, "");
			if (!commit || text === String(raw)) {
				el.innerHTML = original;
				return;
			}
			if (numeric) {
				if (text.trim() && !/\d/.test(text)) {
					frappe.show_alert({ message: __("Please enter a number."), indicator: "orange" });
					el.innerHTML = original;
					return;
				}
				this.preview.commit(node, flt(text));
			} else {
				this.preview.commit(node, text);
			}
		});

		$el.on("keydown.ds-edit", (e) => {
			if (e.key === "Escape") {
				e.preventDefault();
				active.finish(false);
			} else if (e.key === "Enter" && !(multiline && e.shiftKey)) {
				e.preventDefault();
				active.finish(true);
			}
		});
		$el.on("paste.ds-edit", (e) => {
			e.preventDefault();
			const text = (e.originalEvent.clipboardData || window.clipboardData).getData("text/plain");
			document.execCommand("insertText", false, text);
		});
		$el.on("blur.ds-edit", () => setTimeout(() => active.finish(true), 0));
	}

	start_control($el, node) {
		const original = $el.html();
		const is_check = node.fieldtype === "Check";
		const df = is_check
			? { fieldtype: "Select", options: ["Yes", "No"].map((v) => ({ value: v, label: __(v) })) }
			: { fieldtype: node.fieldtype, options: node.options };
		df.fieldname = "ds_inline";
		df.label = "";

		$el.addClass("ds-editing").removeClass("ds-empty").empty();
		const $wrap = $(`<span class="ds-ui ds-control"></span>`).appendTo($el);
		const control = frappe.ui.form.make_control({ df, parent: $wrap, render_input: true, only_input: true });
		const initial = is_check ? (cint(node.value) ? "Yes" : "No") : node.value ?? "";
		control.set_value(initial);

		const read = () => {
			const v = control.get_value();
			return is_check ? (v === "Yes" ? 1 : 0) : v ?? "";
		};
		const active = this._activate((commit) => {
			const value = read();
			if (control.datepicker) control.datepicker.hide();
			$(".awesomplete > ul").attr("hidden", true);
			$el.removeClass("ds-editing").html(original);
			const before = is_check ? cint(node.value) : node.value ?? "";
			if (commit && String(value) !== String(before)) this.preview.commit(node, value);
		});

		// Select/Check commit as soon as a value is picked; the others on Enter or click-away.
		control.df.change = () => {
			if (["Select", "Check"].includes(node.fieldtype)) active.finish(true);
		};
		control.$input.on("keydown", (e) => {
			if (e.key === "Escape") {
				e.preventDefault();
				active.finish(false);
			} else if (e.key === "Enter" && !$(".awesomplete ul:visible li[aria-selected=true]").length) {
				e.preventDefault();
				setTimeout(() => active.finish(true), 50);
			}
		});
		setTimeout(() => control.$input.trigger("focus"), 0);
		this._outside_click($el, active);
	}

	start_rich($el, node) {
		const el = $el[0];
		const original = el.innerHTML;
		$el.addClass("ds-editing").removeClass("ds-empty");
		el.setAttribute("contenteditable", "true");
		el.focus();

		const active = this._activate((commit) => {
			el.removeAttribute("contenteditable");
			$el.removeClass("ds-editing").off(".ds-edit");
			const html = el.innerHTML;
			if (!commit || html === original) {
				el.innerHTML = original;
				return;
			}
			this.preview.commit(node, html);
		});
		$el.on("keydown.ds-edit", (e) => {
			if (e.key === "Escape") {
				e.preventDefault();
				active.finish(false);
			}
		});
		this._outside_click($el, active);
	}
}
