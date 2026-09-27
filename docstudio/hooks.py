app_name = "docstudio"
app_title = "DocStudio"
app_publisher = "Inderajeet"
app_description = "Turn any Frappe record into an editable, Word-ready business document"
app_email = "inderajeetperiyasami210@gmail.com"
app_license = "mit"

# DocStudio depends on Frappe only. ERPNext/HRMS layouts activate at runtime when their
# DocTypes exist (see docstudio.engine.builtin).
required_apps = []

app_include_js = "docstudio.bundle.js"
app_include_css = "docstudio.bundle.css"

boot_session = "docstudio.engine.access.boot_session"

after_install = "docstudio.install.after_install"
after_migrate = "docstudio.install.after_migrate"

# ── DocStudio extension points (other apps declare these in their own hooks.py) ──
# docstudio_templates = [{"key": ..., "label": ..., "doctype": ..., "builder": "dotted.path"}]
# docstudio_model_processors = ["dotted.path"]  # fn(ctx, model)
# docstudio_recalculate = ["dotted.path"]  # fn(doc)
