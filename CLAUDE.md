# DocStudio: notes for future sessions

A standalone Frappe app that adds **Preview & Edit** to every form. It renders the record as a
business document, lets users edit in place, and downloads it as `.docx`.

## Hard rules

- **Frappe only.** Never import ERPNext, HRMS or other apps. ERPNext/HRMS layouts activate at
  runtime only when their DocType exists (`frappe.db.exists("DocType", ...)`).
- Target Frappe v15; keep v16 compatible (no removed APIs, no jQuery-only features that v16 dropped).
- All user-facing strings go through `_()` (Python) or `__()` (JS).
- No free-form or absolute positioning. Layout is flow-based and section-level only, so it maps to Word.
- Editor chrome (dotted underline `.ds-ed`, `.ds-ui` buttons, toolbar) must never reach the `.docx`.

## Architecture: one content model

```
record ─► builder (auto | built-in | custom hook) ─► DocModel JSON ─┬─► JS Renderer (preview HTML)
                     ▲                                             └─► DocxWriter (python-docx)
edits patch (JSON) ──┘  server re-applies the patch to a fresh model on every render/save/export
```

- `engine/model.py` documents the DocModel: section types and node shape. Node ids are
  deterministic (`f:<field>`, `c:<table>:<row>:<field>`, `s:<...>` for sections), so a saved
  patch can be re-applied.
- `engine/patch.py` documents the **edits patch**: `fields`, `rows`, `added_rows`,
  `deleted_rows`, `overrides`, `styles`, `layout`. The browser only ever sends a patch, never HTML
  or layout. Record changes are validated against meta; strict mode (Save to Form) enforces
  write permission, read-only, permlevel and docstatus per field.
- `engine/context.py` (`BuildContext`) decides editability. A node's `editable` flag means the user
  may click it. `writable` means the edit is a typed field value; if false, the edit is a display
  override. In **Save to Form** mode only writable fields are editable. In **Save as Document
  Only** mode everything is editable and nothing touches the record.
- `engine/registry.py` holds `build_model()`, the single entry point, plus template resolution and
  the extension hooks (`docstudio_templates`, `docstudio_model_processors`, `docstudio_recalculate`).
- `engine/auto_layout.py` is the generic layout from meta. `engine/builtin/` holds the
  hand-designed layouts, which use Field Mapping slots (`ctx.mapped(slot, default)`).
- `export/docx_writer.py` walks the same model. **Every rPr/tblPr/tcPr/trPr/pPr child must be
  inserted via `_ensure()`** (schema order), or Word reports the file as corrupt. Complex-script
  fonts (`w:cs`, `w:bCs`, `w:szCs`) are always set, for Tamil.
- `public/js/docstudio/`: `renderer.js` mirrors the writer section by section, `state.js` is the
  patch with undo/redo, `editor.js` handles click-to-edit (Frappe controls for Link/Date/Select/Check),
  `preview.js` is the view controller, `form_button.js` is the global button (registered on
  `form-load` so it runs after DocType scripts).
- The toolbar is mounted inside Frappe's sticky `.page-head > .container`. While the preview is
  open, `body.ds-preview-open` pins the page head (Frappe slides it away on scroll) and the form's
  `page_actions` are hidden, so there is only one Save. Ctrl+S goes to DocStudio through
  `frappe.container.page.save_action`.

- Table formatting in the preview: `patch.styles[<table section id>]` = {table_style: Bordered |
  Minimal} (see `clean_table_style`). Column formatting is `patch.styles["col:<section id>:<field>"]`,
  merged into every cell server-side; a cell's own style wins.
- Opening the preview uses the DocType's current default template; a saved version's edits apply
  on top.

When you change a section type, update **all three**: `model.py` (docs + `iter_nodes`),
`renderer.js`, and `docx_writer.py`.

## Save modes

- Save to Form: `api.save` applies the patch strictly and calls `doc.save()`. Formatting,
  overrides and layout (the "residual") are stored as a DocStudio Document Version.
- Document only: the whole patch goes into a new Document Version, plus a generated .docx. Forced
  for submitted/cancelled records and for users without write permission.
- Opening the preview loads the latest version's patch as the starting point.

## Status

Done: auto layout, editing, save, .docx; themes and formatting; built-in templates, Field
Mapping and Terms Blocks; section layout; column and per-table formatting; tests and docs. Manual test steps per phase are in `docs/TESTING.md`; the
marketplace draft is in `docs/MARKETPLACE.md`.

Later (not built yet): built-ins for Sales Order, RFQ, Purchase Receipt, Payment Entry receipt,
Salary Slip, and experience/relieving letters. Add them to `engine/builtin/layouts.py` and
register them in `BUILTINS` with `requires` and `slot_tables`.

## Conventions

- Python: tabs, double quotes, ruff config in `pyproject.toml`. JS: tabs, ES modules bundled via
  `public/js/docstudio.bundle.js`.
- Whitelisted methods live in `docstudio/api.py`. Every one calls
  `access.check_access()` or an explicit `frappe.has_permission`/`only_for`.

## Testing

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app docstudio
```

Tests call `reset_templates()` (through `make_record`) so templates saved on a dev site don't
leak into assertions. Tests create custom DocTypes at runtime (`tests/utils.py`: `DocStudio Test Record`, child
`DocStudio Test Item`, company-like `DocStudio Test Company`). Nothing test-only ships with the app.
