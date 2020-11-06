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


tokens = ["gzil", "xsgd", "bolt", "carb", "zlp"]
tokens_upper = ["GZIL", "XSGD", "BOLT", "CARB" "ZLP"]

tok_upper_to_down = {"GZIL"  : "gzil",
                     "XSGD"  : "xsgd",
                     "BOLT"  : "bolt",
                     "CARB"  : "carb",
                     "ZLP"   : "zlp"}


###########################
### Update Price Chart ####
###########################

def update_chart(attrname, old, new):
    tok = tok_upper_to_down[new]

    source.data.update(ohlc_1h[tok])


###########################
###  Init Price Chart  ####
###########################

mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zilcrawl"]

ohlcdb = {"xsgd"  : mongodb["ohlc_1h_xsgd"],
          "gzil"  : mongodb["ohlc_1h_gzil"],
          "bolt"  : mongodb["ohlc_1h_bolt"],
          "carb"  : mongodb["ohlc_1h_carb"],
          "zlp"   : mongodb["ohlc_1h_zlp"]}

ohlc_1h = {}
for tok in tokens:
    for x in ohlcdb[tok].find().sort('_id'):
        if tok not in ohlc_1h:
            ohlc_1h[tok] = {}
            ohlc_1h[tok]['time']    = x['time']
            ohlc_1h[tok]['open']    = x['open']
            ohlc_1h[tok]['high']    = x['high']
            ohlc_1h[tok]['low']     = x['low']
            ohlc_1h[tok]['close']   = x['close']
            ohlc_1h[tok]['average'] = x['average']
            ohlc_1h[tok]['color']   = x['color']

        ohlc_1h[tok]['time'].append(x['time'][0])
        ohlc_1h[tok]['open'].append(x['open'][0])
        ohlc_1h[tok]['high'].append(x['high'][0])
        ohlc_1h[tok]['low'].append(x['low'][0])
        ohlc_1h[tok]['close'].append(x['close'][0])
        ohlc_1h[tok]['average'].append(x['average'][0])
        ohlc_1h[tok]['color'].append(x['color'][0])

mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zilcrawl"]

_tok = "xsgd"

ohlcdb = {"xsgd"  : mongodb["ohlc_1h_xsgd"],
          "gzil"  : mongodb["ohlc_1h_gzil"],
          "bolt"  : mongodb["ohlc_1h_bolt"],
          "carb"  : mongodb["ohlc_1h_carb"],
          "zlp"   : mongodb["ohlc_1h_zlp"]}


source = ColumnDataSource(dict(time=[], average=[], low=[], high=[], open=[], close=[], color=[]))

p = figure(plot_height=200, tools="pan,wheel_zoom,box_zoom,reset", x_axis_type="datetime", y_axis_location="right")
p.x_range.follow = "end"
p.x_range.follow_interval = 1000000000
p.x_range.range_padding = 0

p.line(x='time', y='average', alpha=0.2, line_width=3, color='navy', source=source)
p.line(x='time', y='ma', alpha=0.8, line_width=2, color='orange', source=source)
p.segment(x0='time', y0='low', x1='time', y1='high', line_width=2, color='black', source=source)
p.segment(x0='time', y0='open', x1='time', y1='close', line_width=8, color='color', source=source)

layout = column(p, sizing_mode="scale_width", name="line")

curdoc().add_root(layout)

update_chart('tok','XSGD','XSGD')

# Streaming
#for x in ohlcdb['xsgd'].find().sort('_id'):
#    del x['_id']
#    source.stream(x, 4000)



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


_liq = {"gzil" : [],
        "xsgd" : [],
        "bolt" : [],
        "carb" : [],
        "zlp"  : []}

_rate = {"gzil" : [],
         "xsgd" : [],
         "bolt" : [],
         "carb" : [],
         "zlp"  : []}

for tok in tokens:
    mongodb[tok]
    for x in mongodb[tok].find().sort('_id'):
        _liq[tok].append(x['liq_zil'])
        _rate[tok].append(x['rate'])

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


curdoc().title = "Zilgraph - A Zilswap Dashboard"
curdoc().template_variables['stats_names'] = ['total_liq', 'xsgd_liq', 'pairs', 'sales']
curdoc().template_variables['stats'] = {
    'total_liq' : {'icon': 'user',        'value': str(int(total_liq)) + " ZIL", 'change':  4   , 'label': 'Total Liquidity'},
    'xsgd_liq'  : {'icon': 'user',        'value': str(int(_liq['xsgd'][-1])) + " ZIL",   'change':  1.2 , 'label': 'XSGD Liquidity'},
    'pairs'     : {'icon': 'user',        'value': len(tokens), 'change':  0.0 , 'label': 'Verified Tokens'},
    'sales'     : {'icon': 'dollar',      'value': str(int(_rate['gzil'][-1])) + " ZIL",  'change': -0.2 , 'label': 'gZIL Token Price'},
}
