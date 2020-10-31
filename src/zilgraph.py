# -*- coding: utf-8 -*-

import json

import time
from datetime import datetime

from flask import Flask, Response, render_template
import pymongo


app = Flask(__name__)

# Configure MongoDB
mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongodb = mongoclient["zillog"]
        
token = {"xsgd": mongodb["xsgd"], 
         "gzil": mongodb["gzil"]}

token = {"xsgd"  : mongodb["xsgd"], 
         "gzil"  : mongodb["gzil"], 
         "bolt"  : mongodb["bolt"], 
         "zlp"   : mongodb["zlp"]}        


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/gzil-chart-data')
def gzil_chart_data():
    def get_market_data():
        last_id = int(time.time())-60*10*100
        it = 0
        while True:
            myquery = { "_id": { "$gt": last_id } }
            for x in mongodb["gzil"].find(myquery):
                if it%60 == 0:
                    _time = str(datetime.fromtimestamp(x['_id']))
                    _rate = x['rate']
                    json_data = json.dumps({'time': _time, 'value': _rate})
                    yield f"data:{json_data}\n\n"
                last_id = x['_id']
                it+=1
                
            time.sleep(1)

    
    return Response(get_market_data(), mimetype='text/event-stream')

@app.route('/xsgd-chart-data')
def xsgd_chart_data():
    def get_market_data():
        last_id = int(time.time())-60*10*100
        it = 0
        while True:
            myquery = { "_id": { "$gt": last_id } }
            for x in mongodb["xsgd"].find(myquery):
                if it%60 == 0:
                    _time = str(datetime.fromtimestamp(x['_id']))
                    _rate = x['rate']
                    json_data = json.dumps({'time': _time, 'value': _rate})
                    yield f"data:{json_data}\n\n"
                last_id = x['_id']
                it+=1
                
            time.sleep(1)

    return Response(get_market_data(), mimetype='text/event-stream')


@app.route('/gzil-chart-data-live')
def gzil_chart_data_live():
    def get_market_data():
        last_id = int(time.time())-10*100
        while True:
            myquery = { "_id": { "$gt": last_id } }
            for x in mongodb["gzil"].find(myquery):
                _time = str(datetime.fromtimestamp(x['_id']))
                _rate = x['rate']
                json_data = json.dumps({'time': _time, 'value': _rate})
                yield f"data:{json_data}\n\n"
                last_id = x['_id']
                
            time.sleep(1)

    
    return Response(get_market_data(), mimetype='text/event-stream')

@app.route('/xsgd-chart-data-live')
def xsgd_chart_data_live():
    def get_market_data():
        last_id = int(time.time())-10*100
        while True:
            myquery = { "_id": { "$gt": last_id } }
            for x in mongodb["xsgd"].find(myquery):
                _time = str(datetime.fromtimestamp(x['_id']))
                _rate = x['rate']
                json_data = json.dumps({'time': _time, 'value': _rate})
                yield f"data:{json_data}\n\n"
                last_id = x['_id']
                
            time.sleep(1)

    return Response(get_market_data(), mimetype='text/event-stream')

labels = [
    'JAN', 'FEB', 'MAR', 'APR',
    'MAY', 'JUN', 'JUL', 'AUG',
    'SEP', 'OCT', 'NOV', 'DEC'
]

values = [
    967.67, 1190.89, 1079.75, 1349.19,
    2328.91, 2504.28, 2873.83, 4764.87,
    4349.29, 6458.30, 9907, 16297
]

colors = [
    "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
    "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
    "#C71585", "#FF4500", "#FEDCBA", "#46BFBD"]

@app.route('/pie-chart')
def pie():
    def get_market_data():
        last_id = int(time.time())-10*100
        while True:
            myquery = { "_id": { "$gt": last_id } }
            for x in mongodb["gzil"].find(myquery):
                _time = str(datetime.fromtimestamp(x['_id']))
                _liq_zil = x['liq_zil']
                json_data = json.dumps({'time': _time, 'value': _liq_zil})
            
            yield f"data:{json_data}\n\n"
            
            for x in mongodb["xsgd"].find(myquery):
                _time = str(datetime.fromtimestamp(x['_id']))
                _liq_zil = x['liq_zil']
                json_data = json.dumps({'time': _time, 'value': _liq_zil})
            
            yield f"data:{json_data}\n\n"
            
            last_id = x['_id']
                
            time.sleep(1)

    return Response(get_market_data(), mimetype='text/event-stream')
    return render_template('pie_chart.html', title='Bitcoin Monthly Price in USD', max=17000, set=zip(values, labels, colors))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
