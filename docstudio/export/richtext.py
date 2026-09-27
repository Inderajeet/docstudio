"""Parse the restricted rich-text HTML (Quill / sanitized) into blocks of styled runs.

Used by the .docx writer; the preview shows the same HTML directly.
"""

import re
from html.parser import HTMLParser

BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "tr"}
_COLOR_RE = re.compile(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgb\([^)]*\))", re.I)
_BOLD_RE = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
_ITALIC_RE = re.compile(r"font-style\s*:\s*italic", re.I)
_UNDERLINE_RE = re.compile(r"text-decoration[a-z-]*\s*:\s*[^;]*underline", re.I)
_ALIGN_RE = re.compile(r"text-align\s*:\s*(left|center|right|justify)", re.I)


def _hex(color):
	color = color.strip()
	if color.startswith("#") and len(color) == 4:
		return "#" + "".join(c * 2 for c in color[1:])
	m = re.match(r"rgb\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
	if m:
		return "#{:02X}{:02X}{:02X}".format(*(int(x) for x in m.groups()))
	return color


class _Parser(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.blocks = []
		self.style_stack = [{}]
		self.lists = []  # [("ul"|"ol", counter)]
		self.cur = None

	def _block(self, **kw):
		self.cur = {"runs": [], "align": None, "list": None, "heading": None, **kw}
		self.blocks.append(self.cur)

	def _ensure_block(self):
		if self.cur is None:
			self._block()

	def handle_starttag(self, tag, attrs):
		attrs = dict(attrs)
		style = dict(self.style_stack[-1])
		if tag in ("b", "strong"):
			style["bold"] = True
		elif tag in ("i", "em"):
			style["italic"] = True
		elif tag == "u":
			style["underline"] = True
		css = attrs.get("style") or ""
		color = _COLOR_RE.search(css)
		if color:
			style["color"] = _hex(color.group(1))
		if _BOLD_RE.search(css):
			style["bold"] = True
		if _ITALIC_RE.search(css):
			style["italic"] = True
		if _UNDERLINE_RE.search(css):
			style["underline"] = True
		if tag in ("ul", "ol"):
			self.lists.append([tag, 0])
		if tag == "br":
			self._ensure_block()
			self.cur["runs"].append(("\n", dict(style)))
			return
		if tag in BLOCK_TAGS:
			align = None
			m = _ALIGN_RE.search(css)
			if m:
				align = m.group(1).lower()
			for cls in (attrs.get("class") or "").split():
				if cls.startswith("ql-align-"):
					align = cls[len("ql-align-") :]
			kw = {"align": align}
			if tag == "li" and self.lists:
				self.lists[-1][1] += 1
				kw["list"] = (self.lists[-1][0], self.lists[-1][1], len(self.lists))
			if tag.startswith("h") and len(tag) == 2:
				kw["heading"] = int(tag[1])
				style["bold"] = True
			self._block(**kw)
		self.style_stack.append(style)

	def handle_endtag(self, tag):
		if tag in ("ul", "ol") and self.lists:
			self.lists.pop()
		if tag == "br":
			return
		if len(self.style_stack) > 1:
			self.style_stack.pop()
		if tag in BLOCK_TAGS:
			self.cur = None

	def handle_startendtag(self, tag, attrs):
		if tag == "br":
			self._ensure_block()
			self.cur["runs"].append(("\n", dict(self.style_stack[-1])))

	def handle_data(self, data):
		if not data:
			return
		if self.cur is None and not data.strip():
			return
		self._ensure_block()
		self.cur["runs"].append((re.sub(r"[ \t\r\n]+", " ", data), dict(self.style_stack[-1])))


def parse(html):
	p = _Parser()
	p.feed(html or "")
	p.close()
	blocks = []
	for b in p.blocks:
		# Trim leading/trailing whitespace within a block.
		runs = [r for r in b["runs"] if r[0]]
		if runs:
			runs[0] = (runs[0][0].lstrip(" "), runs[0][1])
			runs[-1] = (runs[-1][0].rstrip(" "), runs[-1][1])
		b["runs"] = [r for r in runs if r[0]]
		blocks.append(b)
	# Drop empty trailing blocks but keep deliberate blank lines in the middle.
	while blocks and not blocks[-1]["runs"]:
		blocks.pop()
	return blocks
