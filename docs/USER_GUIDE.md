# DocStudio User Guide

DocStudio turns any Frappe record into a business document that you can edit in place and
download as a Word (`.docx`) file.

## Contents

1. [Installation](#1-installation)
2. [Opening a document](#2-opening-a-document)
3. [Editing](#3-editing)
4. [Saving](#4-saving)
5. [Formatting](#5-formatting)
6. [Tables](#6-tables)
7. [Themes](#7-themes)
8. [Sections and page breaks](#8-sections-and-page-breaks)
9. [Terms Blocks](#9-terms-blocks)
10. [Templates](#10-templates)
11. [Downloading and attaching](#11-downloading-and-attaching)
12. [Settings](#12-settings)
13. [Troubleshooting](#13-troubleshooting)

## 1. Installation

**Frappe Cloud:** install DocStudio from the Marketplace on your site.

**Self-hosted:**

```bash
bench get-app https://github.com/Inderajeet/docstudio --branch main
bench --site your.site install-app docstudio
bench build --app docstudio
```

DocStudio works with Frappe v15 on its own. When ERPNext or HRMS is installed, ready-made layouts
for Quotation, Sales Invoice (GST), Purchase Order, Delivery Note and Job Offer are added
automatically.

## 2. Opening a document

1. Open any saved record, for example a Sales Invoice.
2. Click **Preview & Edit** at the top of the form.

The record appears as an A4 document: letterhead from your Company, a "To" box, number and
date, the items table, totals, terms and a signature. Click **Back to Form** to return.

## 3. Editing

- Values with a **dotted underline** can be edited. Click one, type, and press **Enter** (or
  click elsewhere). **Esc** cancels.
- Link fields show suggestions, dates show a date picker, and Select or Check fields show a
  dropdown.
- In tables, click anywhere in a cell to edit it. Use **+ Add Row** to add a row and **×** to
  remove one.
- Totals are recalculated after each change.
- **Undo / Redo:** the ↶ ↷ buttons, or **Ctrl+Z** / **Ctrl+Y**.

Changed values are highlighted until you save.

## 4. Saving

Click **Save** (or press **Ctrl+S**). The dropdown next to the template and theme decides what
Save does:

- **Save to Form:** writes the changed values back to the record. Your normal permissions
  apply, and read-only fields can't be changed.
- **Save as Document Only:** keeps your changes with the document only. The record isn't
  changed. This is always used for submitted and cancelled records, and for users who can't
  edit the record.

Formatting, reworded text and layout changes are always kept with the document, and they come
back the next time you open the preview.

## 5. Formatting

Click any text in the document, then use the toolbar: font size, **bold**, *italic*,
underline, alignment and colour. The **×** button clears formatting.

While editing a paragraph (for example terms), select a few words to format just those words.

Everything you format is carried into the Word file.

## 6. Tables

- **Format a whole column:** click the column's header (for example *Amount*), then use the
  toolbar. Every cell in the column changes; a cell you formatted yourself keeps its own style.
- **Table style:** click the **S.No** header to select the table, then choose **Bordered** or
  **Minimal** in the toolbar.
- **Hide a column:** hover the header and click the eye icon.

## 7. Themes

Choose a theme from the toolbar: **Business**, **Formal**, **Modern** or **Simple**.

To make your own, open **DocStudio Theme**, open a standard theme, and use **Menu > Duplicate**.
You can change the font (including Noto Sans Tamil), font sizes, colours, table style, header
shading, page size and margins. Set it as the default in **DocStudio Settings**, or on a
template.

## 8. Sections and page breaks

Hover a section to see its tools in the left margin:

- **⋮⋮** drag to move the section up or down;
- **eye icon** hide or show the section (hover a field label to hide a single field);
- **↧** start the section on a new page.

Hidden parts stay dimmed in the preview so you can bring them back, and they are left out of
the Word file.

**Layout** menu:

- **Save layout to template** (administrators): use this arrangement for all future documents
  of this DocType.
- **Reset layout for this document**: undo this document's own layout changes.

## 9. Terms Blocks

Terms Blocks are reusable clauses, like "Payment terms" or "Electrical work terms".

1. Create one in **DocStudio Terms Block**. You can limit it to certain DocTypes.
2. In the preview, pick it from the **Terms** dropdown. It's added to the document and stays
   editable there.
3. To add it automatically, set it as a template's **Default Terms Block**.

## 10. Templates

A **DocStudio Template** controls how a DocType looks. Each DocType can have one default.

- **Auto:** built from the DocType's own sections, tables and fields. Works on any DocType,
  including custom ones.
- **Built-in:** hand-designed layouts for ERPNext / HRMS documents.
- **Custom:** a layout registered by another app (for developers; see the README).

On a template you can also set:

- **Theme** and **Default Terms Block**;
- **Highlight fields** (title, party, date, total, company) if the automatic guess is wrong;
- **Field Mapping** (built-in templates): point a slot at a different field, for example if
  your site uses a custom field for the item description.

Switch templates for one document from the toolbar.

## 11. Downloading and attaching

- **Download .docx** downloads the document as it looks in the preview, including unsaved
  changes.
- The arrow next to it has **Attach .docx to this record**, which saves the file in the
  record's attachments.

Word files use your theme's fonts, with settings that make Tamil and other Indic scripts
display correctly.

## 12. Settings

**DocStudio Settings** (System Manager):

- **Enable DocStudio**, **Default Theme** and **Default Save Mode**.
- **Attach Downloaded .docx to the Record:** keep a copy of every download.
- **Allowed Roles:** leave empty to allow everyone who can read the record.
- **Excluded DocTypes:** hide the Preview & Edit button on these DocTypes.
- **Sync Standard Templates:** re-create the standard themes and built-in templates. Run it
  after installing ERPNext or HRMS.

## 13. Troubleshooting

**I don't see the Preview & Edit button.**
Save the record first. Check that DocStudio is enabled, your role is allowed, and the DocType
isn't excluded in DocStudio Settings. Then reload the page.

**A value isn't editable.**
In *Save to Form* mode, only fields you're allowed to change are editable. Switch to *Save as
Document Only* to change the document's text without changing the record.

**The logo or company address is missing.**
DocStudio reads them from the Company linked on the record. Fill in the Company's logo and
address.

**The built-in layout isn't used.**
Run **Sync Standard Templates** in DocStudio Settings, and check that the template is marked as
the default for that DocType.

Still stuck? See [Support](SUPPORT.md).
