#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 19:37:23 2020

@author: julian
"""

import requests
import json
import pymongo
import time
from datetime import datetime

from pprint import pprint

from pyzil.zilliqa import chain
from pyzil.zilliqa.units import Zil
from pyzil.zilliqa.api import ZilliqaAPI
from pyzil.account import Account
from pyzil.contract import Contract

class zilcrawl:
    def __init__(self):
        
        # Setup GET request
        self.viewblock_zilswap_url = 'https://api.viewblock.io/v1/zilliqa/addresses/zil1hgg7k77vpgpwj3av7q7vv5dl4uvunmqqjzpv2w/txs?page='
        self.viewblock_headers = { 'X-APIKEY': '724842b06be026a7d619bdbdec96b0e25e0174740a39b7502dafa74065dcefc4'}


        # Configure MongoDB
        self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.mongodb = self.mongoclient["zilcrawl"]
        
        # Create database for zilswap contract
        self.zilswap = self.mongodb["zilswap"]
        
        # Set Token accounts
        self.gzil  = Account(address="zil14pzuzq6v6pmmmrfjhczywguu0e97djepxt8g3e")
        self.xsgd  = Account(address="zil1zu72vac254htqpg3mtywdcfm84l3dfd9qzww8t")
        self.bolt  = Account(address="zil1x6z064fkssmef222gkhz3u5fhx57kyssn7vlu0")
        self.zlp   = Account(address="zil1l0g8u6f9g0fsvjuu74ctyla2hltefrdyt7k5f4")
        
        self.token = {"gzil"  : self.gzil,
                      "xsgd"  : self.xsgd,
                      "bolt"  : self.bolt,
                      "zlp"   : self.zlp}
        
        self.tokendb = {"xsgd"  : self.mongodb["xsgd"], 
                        "gzil"  : self.mongodb["gzil"], 
                        "bolt"  : self.mongodb["bolt"], 
                        "zlp"   : self.mongodb["zlp"]}

        self.ohlcdb = {"xsgd"  : self.mongodb["ohlc_1h_xsgd"], 
                       "gzil"  : self.mongodb["ohlc_1h_gzil"], 
                       "bolt"  : self.mongodb["ohlc_1h_bolt"], 
                       "zlp"   : self.mongodb["ohlc_1h_zlp"]}
        
        self.ohlcdb_24h = {"xsgd"  : self.mongodb["ohlc_24h_xsgd"], 
                           "gzil"  : self.mongodb["ohlc_24h_gzil"], 
                           "bolt"  : self.mongodb["ohlc_24h_bolt"], 
                           "zlp"   : self.mongodb["ohlc_24h_zlp"]}
        
        self.decimals = {"zil"   : 12,
                         "gzil"  : 15,
                         "xsgd"  : 6,
                         "bolt"  : 18,
                         "zlp"   : 18}
        
        
        self.trade_cnt = {"gzil"  : 0,
                          "xsgd"  : 0,
                          "bolt"  : 0,
                          "zlp"   : 0}

        
    def run(self, debug=False):
        
        
        viewblock_page = []

        for page in range(1,20):
            try:
                r = requests.get(self.viewblock_zilswap_url + str(page), headers=self.viewblock_headers)
                viewblock_page = json.loads(r.content.decode('utf-8'))
            except:
                print("Viewblock: GET Request failed")
        
            for entry in viewblock_page:
                entry['_id'] = entry['hash']
                try:
                    self.zilswap.insert_one(entry)
                except:
                    print("MongoDB: Insert one failed")
                
                # Print entry info
                date_time = datetime.fromtimestamp(int(entry['timestamp']/1000))
                print("Datetime: " + date_time.strftime("%Y-%m-%d %H:%M:%S"))
                print(entry['_id'])
                
            # Max 3 GET requests per second
            time.sleep(0.5)

    def analyze(self, debug=False):
        cnt_exact_zil = 0
        cnt_exact_token = 0
        for entry in self.zilswap.find():
            if 'data' in entry:
                data = json.loads(entry['data'])
                if '_tag' in data:
                    if data['_tag'] == "SwapExactZILForTokens":
                        cnt_exact_zil+=1
                        self.analyze_swap(entry)
                    if data['_tag'] == "SwapZILForExactTokens":
                        cnt_exact_token+=1
                        
                    
        print("ExactZIL: " + str(cnt_exact_zil))
        print("ExactToken: " + str(cnt_exact_token))
        
        pprint(self.trade_cnt)
        
        
    def analyze_swap(self, entry):
        _timestamp = int(entry['timestamp']/1000)
        date_time = datetime.fromtimestamp(_timestamp)
        print("Datetime: " + date_time.strftime("%Y-%m-%d %H:%M:%S"))
        print(entry['_id'])
        #data = json.loads(entry['data'])
        #print(data['_tag'])
        
        _tok = None
        _success = 0
        try:
                
            for e in entry['events']:
                if e['name'] == "Swapped":
                    pool = e['params']['pool']
                    for tok in self.token:
                        if pool == self.token[tok].address0x:
                            self.trade_cnt[tok]+=1
                            _tok = tok
                            
                if e['name'] == "TransferSuccess":
                    
                    _amount = e['params']['amount']
                    _success = 1

        except:
            pass

        if _success == 1 and _tok != None:
            _tok_amount = int(_amount)*pow(10,-self.decimals[_tok])
            _zil_amount = int(entry['value'])*pow(10,-self.decimals['zil'])
            _rate = _zil_amount / _tok_amount
            
            print("Rate " + _tok + ": " + str(_rate))
            
            new_entry = {"_id": _timestamp,
                         "rate": _rate,
                         "liq_zil": 1000000,
                         "liq_"+_tok: 1000}
            
            print(new_entry)
            print(_tok)
            try:
                self.tokendb[_tok].insert_one(new_entry)
            except Exception as error:
                print("MongoDB: Insert one failed")
                print(error)
                pass
    
    def ohlc(self):
        self.clean("ohlcdb")
        
        arr_1h = {}
        for tok in self.tokendb:        
            for x in self.tokendb[tok].find().sort('_id'):
                h = int(x['_id']/3600)
                if tok in arr_1h:
                    if h in arr_1h[tok]:
                        arr_1h[tok][h].append(x['rate'])
                    else:
                        arr_1h[tok][h] = [x['rate']]
                else:
                    arr_1h[tok] = {}
                    arr_1h[tok][h] = [x['rate']]
        
        arr_24h = {}
        for tok in self.tokendb:        
            for x in self.tokendb[tok].find().sort('_id'):
                d = int(x['_id']/(3600*24))
                if tok in arr_24h:
                    if d in arr_24h[tok]:
                        arr_24h[tok][d].append(x['rate'])
                    else:
                        arr_24h[tok][d] = [x['rate']]
                else:
                    arr_24h[tok] = {}
                    arr_24h[tok][d] = [x['rate']]
                    
        # OHLC
        for tok in arr_1h:
            for h in arr_1h[tok]:
                op = arr_1h[tok][h][0]
                hi = max(arr_1h[tok][h])
                lo = min(arr_1h[tok][h])
                cl = arr_1h[tok][h][-1]
                av = sum(arr_1h[tok][h]) / len(arr_1h[tok][h])
                color = "green" if op < cl else "red"
                
                new_entry = {"_id"     : h,
                             "time"    : [h*3600*1000],
                             "open"    : [op],
                             "high"    : [hi],
                             "low"     : [lo],
                             "close"   : [cl],
                             "average" : [av],
                             "color"   : [color]}
                
                try:
                    self.ohlcdb[tok].insert_one(new_entry)
                except:
                    print("Oooops..")
                    pass
                
        for tok in arr_24h:
            for d in arr_24h[tok]:
                op = arr_24h[tok][d][0]
                hi = max(arr_24h[tok][d])
                lo = min(arr_24h[tok][d])
                cl = arr_24h[tok][d][-1]
                av = sum(arr_24h[tok][d]) / len(arr_24h[tok][d])
                color = "green" if op < cl else "red"
                
                new_entry = {"_id"     : d,
                             "time"    : [d*3600*24*1000],
                             "open"    : [op],
                             "high"    : [hi],
                             "low"     : [lo],
                             "close"   : [cl],
                             "average" : [av],
                             "color"   : [color]}
                
                try:
                    self.ohlcdb_24h[tok].insert_one(new_entry)
                except:
                    #print("Oooops..")
                    pass
        
        
    def clean(self, db):
        if db == "tokendb":
            for tok in self.tokendb:
                self.tokendb[tok].delete_many({})
        
        if db == "ohlcdb":
            for tok in self.ohlcdb:
                self.ohlcdb[tok].delete_many({})
                
            for tok in self.ohlcdb_24h:
                self.ohlcdb_24h[tok].delete_many({})
            
    def mrproper(self):
        self.zilswap.delete_many({})
            
            
crawler = zilcrawl()

crawler.ohlc()

while True:
    sec_to_next_hour = 3600 - int(time.time()) % 3600

    print(sec_to_next_hour)
    if sec_to_next_hour < 60:
        crawler.run()
        crawler.analyze()
        crawler.ohlc()
        time.sleep(60)
        
    time.sleep(1)

#crawler.clean("ohlcdb")
#crawler.mrproper()



