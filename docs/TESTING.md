# Testing DocStudio on your bench

## One-time setup

```bash
cd ~/frappe-bench
bench --site <site> install-app docstudio
bench build --app docstudio
bench start
```

For a quick sample record on any site (including a Frappe-only site):

```bash
bench --site <site> execute docstudio.tests.utils.make_record
```

This creates the `DocStudio Test Record` custom DocType, a child table, a company-like DocType,
and one record. Open **DocStudio Test Record** from the awesome bar.

Automated tests:

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app docstudio
```

## Phase 1: button, auto layout, editing, Save, .docx

1. Open any saved record, such as a DocStudio Test Record, a Project Purchase Order or a ToDo.
   **Preview & Edit** should be in the toolbar. It should not appear on new/unsaved records,
   Single DocTypes, or DocTypes listed in *DocStudio Settings > Excluded DocTypes*.
2. Click it. Check that you see an A4 page with the letterhead (from the Company link), title,
   a "To" box, number/date, sections, a boxed column layout, the items table with S.No, totals
   and a signature. Hidden and print-hidden fields must not appear.
3. The form's own Save and menu buttons are hidden. Only the DocStudio toolbar has Save.
4. Click an underlined value and change it:
   - Enter commits and Esc cancels.
   - A Link field gives autocomplete; a Date field gives a date picker.
5. Use **+ Add Row**, change Qty/Rate, and watch the amount update. Hover a row and click × to
   remove it.
6. Try Ctrl+Z / Ctrl+Y.
7. Press **Save** (or Ctrl+S), then go **Back to Form**. The values should be saved.
8. Make a change and click **Back to Form**. You should get an unsaved-changes warning.
9. Click **Download .docx** and open it in Word. It should match the preview, with no dotted
   underlines and no buttons.
10. Open a **submitted** record. The mode shows "Document only"; everything is editable; Save
    creates a *DocStudio Document Version* and does not change the record. Reopen the preview
    and your edits are still there.

## Phase 2: themes, formatting toolbar, highlight fields

1. Switch between the Business, Formal, Modern and Simple themes. The page, table style and
   colors should change.
2. Click the title, then use size, bold, italic, underline, alignment and color. Download and
   check the same formatting in Word.
3. Click inside a Text Editor block (such as Notes), select a few words and press **B**. Only
   that selection becomes bold.
4. Scroll a long document. The toolbar must stay pinned in the same place, on every DocType.
5. In *DocStudio Template*, create a template for a DocType and set **Party Field** to another
   field. The "To" box should now show that field.
6. Create a theme with **Noto Sans Tamil**, type Tamil text in a field, and download. The Tamil
   text should render in Word.

## Phase 3: built-in templates, Field Mapping, Terms Blocks

1. In *DocStudio Settings*, click **Sync Standard Templates**. On dev.localhost it creates
   Quotation, Purchase Order and Delivery Note templates. Sales Invoice is skipped because the
   site's Sales Invoice is a custom DocType; Job Offer needs HRMS.
2. Open a Quotation, Purchase Order or Delivery Note (you need at least one record). The built-in
   layout is used, with GST/HSN columns shown only when those fields have values.
3. In a built-in template's **Field Mapping**, point a slot at a different field (for example
   `item_description` to `description`) and check the preview. An invalid fieldname is rejected
   on save.
4. Create a *DocStudio Terms Block* (optionally limited to some DocTypes). In the preview, pick
   it from the **Terms** dropdown, edit its text and Save. Reopen the preview and it is still
   there. Set it as a template's **Default Terms Block** to include it automatically.

## Phase 4: section layout

1. Hover a section and drag it by the ⋮⋮ handle in the left margin.
2. Use the eye icons to hide a section, a field (hover a label) or a table column (hover the
   header). Use ↧ to add a page break. Hidden items stay visible but dimmed in the preview and
   are left out of the .docx.
3. As an admin, choose **Layout > Save layout to template**. New documents of that DocType use
   the arrangement. **Layout > Reset layout** clears the current document's own changes.

## Frappe-only check (no ERPNext)

```bash
bench new-site docstudio.localhost --admin-password admin
bench --site docstudio.localhost install-app docstudio
bench --site docstudio.localhost set-config developer_mode 1
bench --site docstudio.localhost execute docstudio.tests.utils.make_record
bench --site docstudio.localhost set-config allow_tests true
bench --site docstudio.localhost run-tests --app docstudio
```

Install and sync should succeed with no built-in templates created, and every test that needs
ERPNext skips itself.

## Tables and columns

1. In the preview, click the **S.No** header to select the whole table, then switch it between
   Bordered and Minimal in the toolbar.
2. Click a column header (e.g. Amount) and press **B** to make the whole column bold.
3. Click anywhere in a cell, not just on its text, to edit it. Download the .docx and check that
   the table style and column formatting are there.
