app_name = "docstudio"
app_title = "DocStudio"
app_publisher = "Inderajeet"
app_description = "Turn any Frappe record into an editable, Word-ready business document"
app_email = "inderajeetperiyasami210@gmail.com"
app_license = "mit"

required_apps = []

app_include_js = "docstudio.bundle.js"
app_include_css = "docstudio.bundle.css"

boot_session = "docstudio.engine.access.boot_session"

after_install = "docstudio.install.after_install"
after_migrate = "docstudio.install.after_migrate"
