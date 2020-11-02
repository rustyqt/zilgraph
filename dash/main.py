from collections import Counter
from math import pi

import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, gridplot, row
from bokeh.models import (ColumnDataSource, DataTable, NumberFormatter,
                          RangeTool, StringFormatter, TableColumn, HoverTool, Select, Slider, Div)
from bokeh.palettes import Spectral4
from bokeh.plotting import figure
from bokeh.transform import cumsum

import json

import time
from datetime import datetime

import pymongo



tokens = ["gzil", "xsgd", "bolt", "zlp"]
tokens_upper = ["GZIL", "XSGD", "BOLT", "ZLP"]

tok_upper_to_down = {"GZIL"  : "gzil", 
                     "XSGD"  : "xsgd", 
                     "BOLT"  : "bolt", 
                     "ZLP"   : "zlp", 
                     "ZYF"   : "zyf", 
                     "SERGS" : "sergs"}

_time = {}
_rate = {}
_liq = {}


###########################
### Update Price Chart ####
###########################

def update_chart(attrname, old, new):
    mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mongodb = mongoclient["zillog"]
    
    _tok = tok_upper_to_down[new]
    
    for tok in tokens:
        _time[tok] = np.empty([0,1], dtype=np.datetime64)
        _rate[tok] = np.empty([0,1], dtype=float)
        _liq[tok]  = np.empty([0,1], dtype=float)
        
        for x in mongodb[tok].find():
            _time[tok] = np.append(_time[tok], np.datetime64(x['_id'], 's'))
            _rate[tok] = np.append(_rate[tok], x['rate'])
            _liq[tok]  = np.append(_liq[tok], x['liq_zil'])

    source.data.update(dict(date=_time[_tok][-min(_len):], close=_rate[_tok][-min(_len):]))


    
###########################
###  Init Price Chart  ####
###########################

mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zillog"]

_tok = tok_upper_to_down['XSGD']

_len = []
for tok in tokens:
    _time[tok] = np.empty([0,1], dtype=np.datetime64)
    _rate[tok] = np.empty([0,1], dtype=float)
    _liq[tok]  = np.empty([0,1], dtype=float)
    
    for x in mongodb[tok].find():
        _time[tok] = np.append(_time[tok], np.datetime64(x['_id'], 's'))
        _rate[tok] = np.append(_rate[tok], x['rate'])
        _liq[tok]  = np.append(_liq[tok], x['liq_zil'])
    
    _len.append(len(_time[tok]))
    
min(_len)
    
source = ColumnDataSource(data=dict(date=_time[_tok][-min(_len):], close=_rate[_tok][-min(_len):]))
            
#upper_bound = int(len(_time[_tok][-400:])-1)
#lower_bound = int(len(_time[_tok][-400:])/2)

upper_bound = int(len(_time[_tok])-1)
lower_bound = int(len(_time[_tok])-min(_len)/2)

#upper_bound = len(_time[_tok])-1
#lower_bound = len(_time[_tok])-min(_len)+1

p = figure(plot_height=110, tools="", toolbar_location=None, #name="line",
           x_axis_type="datetime", x_range=(_time[_tok][lower_bound], _time[_tok][upper_bound]), sizing_mode="scale_width")

p.line('date', 'close', source=source, line_width=2, alpha=0.7)
p.yaxis.axis_label = 'ZIL'
p.background_fill_color="#f5f5f5"
p.grid.grid_line_color="white"

select = figure(plot_height=50, plot_width=800, y_range=p.y_range,
                x_axis_type="datetime", y_axis_type=None,
                tools="", toolbar_location=None, sizing_mode="scale_width")

range_rool = RangeTool(x_range=p.x_range)
range_rool.overlay.fill_color = "navy"
range_rool.overlay.fill_alpha = 0.2

select.line('date', 'close', source=source)
select.ygrid.grid_line_color = None
select.add_tools(range_rool)
select.toolbar.active_multi = range_rool
select.background_fill_color="#f5f5f5"
select.grid.grid_line_color="white"
select.x_range.range_padding = 0.01

hover = HoverTool()
hover.tooltips = """
<div style=padding=5px>Time:@date</div>
<div style=padding=5px>Rate:@close</div>
"""
hover.mode = "vline"

p.add_tools(hover)

layout = column(p, select, sizing_mode="scale_width", name="line")

curdoc().add_root(layout)
    

###########################
###    Dropdown Menu   ####
###########################


dropdown = Select(value="XSGD", options=tokens_upper, name="dropdown")
dropdown.on_change('value', update_chart)

curdoc().add_root(dropdown)


###########################
###    Donut chart     ####
###########################


# Configure MongoDB
mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zillog"]

pie_dict = {}
for tok in tokens:
    pie_dict[tok.upper()] = int(_liq[tok][-1])

print(pie_dict)

x = Counter(pie_dict)

data = pd.DataFrame.from_dict(dict(x), orient='index').reset_index().rename(index=str, columns={0:'value', 'index':'token'})
data['angle'] = data['value']/sum(x.values()) * 2*pi
data['color'] = Spectral4

region = figure(plot_height=350, toolbar_location=None, outline_line_color=None, sizing_mode="scale_both", name="region", x_range=(-0.5, 0.8))

region.annular_wedge(x=-0, y=1, inner_radius=0.2, outer_radius=0.32,
                  start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                  line_color="white", fill_color='color', legend_group='token', source=data)

region.axis.axis_label=None
region.axis.visible=False
region.grid.grid_line_color = None
region.legend.label_text_font_size = "1.7em"
region.legend.spacing = 5
region.legend.glyph_height = 25
region.legend.label_height = 25

# configure so that no drag tools are active
region.toolbar.active_drag = None


###########################
###        Table       ####
###########################

table_dict = {}
table_dict["tok"]  = []
table_dict["rate"] = []
table_dict["liq"]  = []
for tok in tokens_upper:
    table_dict["tok"].append(tok)
    table_dict["rate"].append(round(_rate[tok_upper_to_down[tok]][-1],2))
    table_dict["liq"].append(int(_liq[tok_upper_to_down[tok]][-1]))


pdsource = ColumnDataSource(data=pd.DataFrame(table_dict))

columns = [
    TableColumn(field="tok", title="Token", formatter=StringFormatter(text_align="center")),
    TableColumn(field="rate", title="Price [ZIL]",  formatter=StringFormatter(text_align="center")),
    TableColumn(field="liq", title="Liquitidy [ZIL]", formatter=NumberFormatter(text_align="center")),
]
table = DataTable(source=pdsource, columns=columns, height=210, width=330, name="table", sizing_mode="scale_both")

#layout = row(region, table)
curdoc().add_root(region)
curdoc().add_root(table)


###########################
###        Setup       ####
###########################


total_liq = 0.0
for tok in tokens:
    total_liq += _liq[tok][-1]


curdoc().title = "Zilswap Dashboard"
curdoc().template_variables['stats_names'] = ['total_liq', 'xsgd_liq', 'pairs', 'sales']
curdoc().template_variables['stats'] = {
    'total_liq' : {'icon': 'user',        'value': str(int(total_liq)) + " ZIL", 'change':  4   , 'label': 'Total Liquidity'},
    'xsgd_liq'  : {'icon': 'user',        'value': str(int(_liq['xsgd'][-1])) + " ZIL",   'change':  1.2 , 'label': 'XSGD Liquidity'},
    'pairs'     : {'icon': 'user',        'value': len(tokens), 'change':  0.0 , 'label': 'Verified Tokens'},
    'sales'     : {'icon': 'dollar',      'value': str(int(_rate['gzil'][-1])) + " ZIL",  'change': -0.2 , 'label': 'gZIL Token Price'},
}





















