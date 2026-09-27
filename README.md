# DocStudio

**Turn any Frappe record into a real business document. Edit it in place and download it as Word.**

DocStudio adds a **Preview & Edit** button to every form. It renders the record as a clean,
A4-proportioned business document (letterhead, "To" box, number and date, items table, totals,
terms, signature). You click any underlined value to change it, then download a `.docx` that
looks the same as the preview.

It works on **any DocType** out of the box. Hand-designed layouts for common ERPNext and HRMS
documents switch on automatically when those apps are installed.

## Features

- **Works on every DocType.** The auto layout is built from the DocType's own sections, column
  breaks, child tables, currency and date fields. There is no per-DocType setup.
- **Looks like a document, not a form.** Letterhead from the linked Company (address, phone,
  email, tax ID, logo), a party box, number and date on the right, a bordered items table with
  S.No, bold totals, rich-text terms, and a signature block.
- **Edit in place.** Click a dotted-underlined value to edit it. Link fields get autocomplete,
  dates get a date picker, and Select/Check fields get dropdowns. You can add and remove child
  table rows. Totals recalculate on the server. Undo/redo (Ctrl+Z / Ctrl+Y) works for the whole
  session.
- **One Save button.** While the preview is open, the form's own Save is hidden, and Ctrl+S saves
  the document.
  - **Save to Form** writes values back to the record, respecting permissions and read-only fields.
  - **Save as Document Only** keeps the edits with the document (a *DocStudio Document Version*)
    and never changes the record. This mode is always used for submitted and cancelled records.
- **Formatting toolbar.** Font size, bold, italic, underline, alignment and color, all carried
  into the `.docx`. Click a table's column header to format the whole column, or its S.No
  header to switch that table between Bordered and Minimal. The toolbar stays in the same place
  on every DocType while you scroll.
- **Themes.** Business, Formal, Modern and Simple ship with the app. You can create your own:
  font (including Noto Sans Tamil), sizes, colors, table style (Bordered or Minimal), page size
  and margins.
- **Section layout.** Drag sections by their handle, show or hide any section, field or table
  column, and insert page breaks. Admins can save the arrangement to the template for all future
  documents.
- **Terms Blocks.** Reusable clauses such as "Electrical work terms" or "Plumbing terms". Pick
  one in the preview; it drops in and stays editable for that document.
- **Word export (python-docx).** Page size and margins, fonts with complex-script (`w:cs`)
  settings so Tamil renders correctly, shaded table headers that repeat on every page, and
  bordered boxes. Editor chrome never reaches the file.

## Requirements

- Frappe v15 (v16 compatible). DocStudio depends on **Frappe only**.
- `python-docx` (installed automatically).
- Optional: ERPNext and/or HRMS, for the built-in templates below.

## Installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/Inderajeet/docstudio --branch main
bench --site your.site install-app docstudio
bench build --app docstudio
```

Installing (and every `bench migrate`) creates the standard themes and any built-in templates
whose DocType exists on the site.

## Quick start

1. Open any saved record. Click **Preview & Edit**.
2. Click an underlined value to edit it. Use the toolbar to switch template, theme or terms.
3. Click **Save**, or **Download .docx**.

## Configuration

**DocStudio Settings**

- Enable DocStudio, and limit it to certain roles (empty means everyone who can read the record).
- Exclude DocTypes.
- Choose the default theme and the default save mode.
- Attach downloaded files to the record, if you want.
- **Sync Standard Templates** re-creates the shipped themes and built-in templates. Run it after
  installing ERPNext or HRMS.

**DocStudio Template** (one per layout; mark one as default per DocType)

- **Type:** Auto (from meta), Built-in (shipped layouts), or Custom (registered by another app).
- **Highlight fields:** title, party, date, total and company. Unset fields are guessed from
  names and labels.
- **Default Terms Block** and **Layout** (section order and visibility, set from the preview).
- **Field Mapping:** maps each slot of a built-in layout to a fieldname, so renamed or custom
  fields work without code.

**Built-in templates**

These activate only when the DocType exists and has the fields the layout needs:

| Template | DocType | App |
|---|---|---|
| Quotation (Standard) | Quotation | ERPNext |
| Sales Invoice (GST) | Sales Invoice | ERPNext (GSTIN, HSN/SAC and place of supply when present) |
| Purchase Order (Standard) | Purchase Order | ERPNext |
| Delivery Note (Standard) | Delivery Note | ERPNext |
| Job Offer Letter | Job Offer | HRMS |

## Permissions and security

- Preview and export require **read** permission on the record. Save to Form requires **write**
  permission and is checked field by field (read-only, permlevel, docstatus).
- The browser only sends an *edits patch*. The server rebuilds the document from the database,
  validates every fieldname against the DocType's meta, and sanitizes rich text.

## For developers

### Custom templates (extension point)

A site-specific app can register its own layout without touching DocStudio:

```python
# your_app/hooks.py
docstudio_templates = [
	{
		"key": "acme_po",
		"label": "ACME Purchase Order",
		"doctype": "Purchase Order",
		"builder": "your_app.docstudio.purchase_order.build",
	}
]
```

```python
# your_app/docstudio/purchase_order.py
from docstudio.engine import auto_layout
from docstudio.engine import model as m


def build(ctx):
	sections = auto_layout.build_sections(ctx)  # start from the auto layout, or build from scratch
	note = ctx.text("acme:note", "Deliveries accepted 9am-5pm only.", style={"italic": True})
	sections.insert(-1, m.section("s:acme_note", "text", node=note))
	return sections
```

Then create a **DocStudio Template** with type *Custom* and layout key `acme_po`. The layout
gets themes, editing, formatting, layout controls and `.docx` export for free, because
everything works on the same content model.

### Other hooks

| Hook | Purpose |
|---|---|
| `docstudio_model_processors` | `fn(ctx, model)`: adjust any model after it is built |
| `docstudio_recalculate` | `fn(doc)`: refresh computed values in the preview (for DocTypes without `calculate_taxes_and_totals`) |

### Architecture and tests

The preview and the `.docx` writer share one content model (`docstudio/engine/model.py`), so
what you see is what you download. Manual test steps are in [docs/TESTING.md](docs/TESTING.md).

```bash
bench --site your.site set-config allow_tests true
bench --site your.site run-tests --app docstudio
```

## Support

Questions and bug reports: open a GitHub issue or email cipstudioz@gmail.com.

## License

MIT
