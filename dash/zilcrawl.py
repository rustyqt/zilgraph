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
import sys
from datetime import datetime

from pprint import pprint

from pyzil.account import Account

from zillog import zillog

from pathlib import Path


class zilcrawl:
    def __init__(self):
        
        self.viewblock_zilswap_url = 'https://api.viewblock.io/v1/zilliqa/addresses/zil1hgg7k77vpgpwj3av7q7vv5dl4uvunmqqjzpv2w/txs?page='
        try:
            fp_viewblock_api = open(str(Path.home()) + "/.viewblock.json")
        except:
            print("Failed to connect to Viewblock API")
            print("A ~/.viewblock.json file is required in your home directory with the format:")
            print("{")
            print("  \"X-APIKEY\": {")
            print("    \"key\"    : \"<key_string>\",")
            print("    \"secret\" : \"<secret_string>\"")
            print("  }")
            print("}")
            sys.exit()
        
        apikey = json.load(fp_viewblock_api)["X-APIKEY"]
        self.viewblock_headers = { 'X-APIKEY': apikey["key"]}

        # Configure MongoDB
        self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.mongodb = self.mongoclient["zilcrawl"]
        
        # Create database for zilswap contract
        self.zilswap = self.mongodb["zilswap"]
        
        # Load Zilgraph JSON 
        fp_json = open("zilgraph.json")
        self.tokens = json.load(fp_json)["tokens"]
        
        # Setup dictionaries
        self.token = {}
        self.tokendb = {}
        self.ohlcdb_1h = {}
        self.ohlcdb_24h = {}
        self.decimals = {"zil" : 12}
        self.trade_cnt = {}
        for tok in self.tokens:
            self.token[tok]      = Account(address=self.tokens[tok]["addr"])
            self.tokendb[tok]    = self.mongodb[tok]
            self.ohlcdb_1h[tok]  = self.mongodb["ohlc_1h_" + tok]
            self.ohlcdb_24h[tok] = self.mongodb["ohlc_24h_" + tok]
            self.decimals[tok]   = self.tokens[tok]["decimals"]
            self.trade_cnt[tok]  = 0
            
    # Viewblock Crawler
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

    # Viewblock Database Crawler
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
    
    # Calc OHLC
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
                    self.ohlcdb_1h[tok].insert_one(new_entry)
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
            for tok in self.ohlcdb_1h:
                self.ohlcdb_1h[tok].delete_many({})
                
            for tok in self.ohlcdb_24h:
                self.ohlcdb_24h[tok].delete_many({})
            
    def mrproper(self):
        self.zilswap.delete_many({})
            
# Instantiate Zillogger
zl = zillog()

crawler = zilcrawl()
#crawler.run()
crawler.analyze()
crawler.ohlc()

while True:
    # Run Zillogger
    zl.run()
    
    # Check time to next full hour
    sec_to_next_hour = 3600 - int(time.time()) % 3600
    print("Countdown: " + str(sec_to_next_hour))
    
    if sec_to_next_hour < 60:
        crawler.run()
        crawler.analyze()
        crawler.ohlc()
        time.sleep(50)
    
    # Sleep for 10 sec
    time.sleep(10)
    
    
    
#crawler.mrproper()



