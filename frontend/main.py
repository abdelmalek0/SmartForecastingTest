from fasthtml.common import *
from utils.ui_constants import *
from routes.home import home
from routes.datasources import datasources
from routes.datapoints import datapoints

app = FastHTML(
    hdrs=(hlink, tlink, dlink, css, apex_charts, alpine, jq, 
          dt_css, dt_js, datetime_picker, datetime_picker_extras, 
          datetime_picker_theme), 
    default_hdrs=False
)

app.add_route('/', home)
app.add_route('/datasources', datasources)
app.add_route('/datapoints/', datapoints)
app.add_route('/datapoints/{datasource_id}', datapoints)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host='0.0.0.0', port=3000, reload=True)