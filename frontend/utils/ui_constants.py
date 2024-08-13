from fasthtml.common import *

jq = Script(src="https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js")
dt_css = Link(rel="stylesheet", type="text/css", href='https://cdn.datatables.net/2.1.3/css/dataTables.dataTables.min.css')
dt_js = Script(src='https://cdn.datatables.net/2.1.3/js/dataTables.min.js')
hlink = Script(src='https://unpkg.com/htmx.org@1.9.10', )
hlink_extras = Script(src="https://unpkg.com/htmx.org/dist/ext/json-enc.js")
tlink = Script(src="https://cdn.tailwindcss.com")
alpine = Script(src="//unpkg.com/alpinejs", defer='')
apex_charts = Script(src="https://cdn.jsdelivr.net/npm/apexcharts")
# moment_plugin = Script(src='https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.1/moment.min.js')

# moment_plugin_extras = Script(src='https://cdn.jsdelivr.net/npm/flatpickr@4.6.9/dist/plugins/momentPlugin.min.js')
# blink = Script(src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js", integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz")
dlink = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.css")
css = Style('''
    html, body {
        background-color: white;
        color: black;
        height: 100vh;
        width: 100vw;
        font-family: 'Helvetica';
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        overflow: hidden; /* prevent scrolling */
    }

    body > div {
        height: calc(100vh - 10px); /* subtract the padding (5px top + 5px bottom) */
        width: calc(100vw - 10px);  /* subtract the padding (5px left + 5px right) */
        margin: 0;
        padding: 5px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: stretch;
        box-sizing: border-box;
    }

''')
datetime_picker = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css")
datetime_picker_extras = Script(src="https://cdn.jsdelivr.net/npm/flatpickr")
datetime_picker_theme = Link(rel="stylesheet", type="text/css", href="https://npmcdn.com/flatpickr/dist/themes/material_blue.css")

navbar_item_style = "width: 150px; margin: 0px 5px; text-align: center; border-radius: 30px; vertical-align: middle; line-height: 50px; "
toggled_style = "background-color: rgb(220 220 220);"
no_decoration_style = "text-decoration: none; color: black;"

meta = Meta(name='viewport', content='width=device-width, initial-scale=1')
