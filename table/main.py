from collections import Counter
from math import pi

import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, gridplot, row
from bokeh.models import (ColumnDataSource, DataTable, NumberFormatter,
                          RangeTool, StringFormatter, TableColumn, HoverTool, Select, Slider, Div)
from bokeh.palettes import Category20
from bokeh.plotting import figure
from bokeh.transform import cumsum

import json

import time
from datetime import datetime

import pymongo



        
###########################
###  Init Price Chart  ####
###########################

mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zilcrawl"]

# Load Zilgraph JSON 
fp_json = open("zilswap/zilgraph.json")
tokens = json.load(fp_json)["tokens"]


###########################
###    Donut chart     ####
###########################


# Configure MongoDB
mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zillog"]

# Legacy dictionaries (to be replaced)
_liq = {}
_rate = {}
for tok in tokens:
    _liq[tok] = []
    _rate[tok] = []
    
for tok in tokens:
    for x in mongodb[tok].find().sort('_id'):
        _liq[tok].append(x['liq_zil'])
        _rate[tok].append(x['rate'])
        
###########################
###        Table       ####
###########################

table_dict = {}
table_dict["tok"]  = []
table_dict["rate"] = []
table_dict["liq"]  = []
for tok in tokens:
    table_dict["tok"].append(tok.upper())
    table_dict["rate"].append(round(_rate[tok][-1],2))
    table_dict["liq"].append(int(_liq[tok][-1]))

# Create Panda data frame
df = pd.DataFrame(table_dict)

# Sort by Liquidity
df.sort_values(by=['liq'], inplace=True, ascending=False)

pdsource = ColumnDataSource(data=df)

columns = [
    TableColumn(field="tok", title="Token", formatter=StringFormatter(text_align="center")),
    TableColumn(field="rate", title="Price [ZIL]",  formatter=StringFormatter(text_align="center")),
    TableColumn(field="liq", title="Liquitidy [ZIL]", formatter=NumberFormatter(text_align="center")),
]
table = DataTable(source=pdsource, columns=columns, height=232, width=330, name="table", sizing_mode="scale_both")

curdoc().add_root(table)


###########################
###        Setup       ####
###########################

curdoc().title = "Zilgraph - A Zilswap Dashboard"



