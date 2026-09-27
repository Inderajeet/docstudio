// Small helpers shared by the preview modules.

export const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

export const text_html = (v) => esc(v).replace(/\n/g, "<br>");

export const clone = (o) => JSON.parse(JSON.stringify(o));

// CSS font stacks that approximate what Word will use (Carlito/Caladea are metric-compatible
// with Calibri/Cambria on Linux). Tamil falls back to the same fonts Word uses for w:cs.
const STACKS = {
	Arial: `Arial, "Liberation Sans", Helvetica, sans-serif`,
	Calibri: `Calibri, Carlito, "Segoe UI", sans-serif`,
	Cambria: `Cambria, Caladea, Georgia, serif`,
	Georgia: `Georgia, serif`,
	"Times New Roman": `"Times New Roman", "Liberation Serif", Times, serif`,
	Verdana: `Verdana, sans-serif`,
	"Noto Sans": `"Noto Sans", sans-serif`,
	"Noto Serif": `"Noto Serif", serif`,
	"Noto Sans Tamil": `"Noto Sans Tamil", "Noto Sans", sans-serif`,
};

export function font_stack(family) {
	const base = STACKS[family] || `"${family}", sans-serif`;
	return `${base}, "Nirmala UI", "Noto Sans Tamil"`;
}

let fonts_loaded = false;
export function ensure_web_fonts(family) {
	if (fonts_loaded || !String(family || "").startsWith("Noto")) return;
	fonts_loaded = true;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href =
		"https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&family=Noto+Sans+Tamil:wght@400;700&family=Noto+Serif:wght@400;700&display=swap";
	document.head.appendChild(link);
}

export const PAGE_MM = { A4: [210, 297], Letter: [215.9, 279.4] };

export function style_css(style, { block = false } = {}) {
	if (!style) return "";
	const out = [];
	if (style.bold) out.push("font-weight:700");
	if (style.bold === false) out.push("font-weight:400");
	if (style.italic) out.push("font-style:italic");
	if (style.underline) out.push("text-decoration:underline");
	if (style.size) out.push(`font-size:${Number(style.size)}pt`);
	if (style.color && /^#[0-9a-fA-F]{6}$/.test(style.color)) out.push(`color:${style.color}`);
	if (style.align && block) out.push(`text-align:${style.align}`);
	if (style.align && !block) out.push(`display:inline-block;width:100%;text-align:${style.align}`);
	return out.join(";");
}

export function debounce(fn, ms) {
	let t;
	return (...args) => {
		clearTimeout(t);
		t = setTimeout(() => fn(...args), ms);
	};
}
