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

from pyzil.zilliqa import chain
from pyzil.account import Account
from pyzil.contract import Contract
from pyzil.zilliqa.units import Zil
from pyzil.zilliqa.api import ZilliqaAPI

from pyzil.zilliqa.chain import active_chain

from pathlib import Path

from elasticsearch import Elasticsearch

class zilcrawl:
    def __init__(self):
        
        # Elasticsearch
        self.es = Elasticsearch()
        
        # Configure MongoDB
        self.mongoclient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.mongodb = self.mongoclient["zilcrawl"]

        # Set mainnet
        chain.set_active_chain(chain.MainNet)  
        
        # Set contract
        _addr = "zil1hgg7k77vpgpwj3av7q7vv5dl4uvunmqqjzpv2w"
        self.contract = Contract.load_from_address(_addr, load_state=True)
        
        # Set pyzil default API endpoint
        # active_chain.api = ZilliqaAPI("https://ssn.zillet.io/")
        active_chain.api = ZilliqaAPI("http://localhost:4201")

        # Delete existing index
        self.es.indices.delete(index='zilcrawl', ignore=[400, 404])
        
        block_begin = 811030  # Zilswap Contract Creation
        block_end   = 974560  # Circa 17.01.2021
        
        for txblock in range(block_begin, block_end):
            print(str(txblock-block_begin) + " of " + str(block_end-block_begin))
            try:
                ublocks = chain.active_chain.api.GetTransactionsForTxBlock(str(txblock))
            
                for ublock in ublocks:
                    for tx_hash in ublock:
                        tx = chain.active_chain.api.GetTransaction(tx_hash)
                        
                        # Serialize events and transitions                        
                        if 'receipt' in tx:
                            if 'event_logs' in tx['receipt']:
                                tx['receipt']['event_logs'] = json.dumps(tx['receipt']['event_logs'])
                            if 'transitions' in tx['receipt']:
                                tx['receipt']['transitions'] = json.dumps(tx['receipt']['transitions'])
                                
                        #print("----------------------")
                        #print("-- Modified Mapping --")
                        #print("----------------------")
                        #pprint(tx)
                        try:
                            self.es.create("zilcrawl", tx['ID'], tx, ignore=[409])
                        except Exception as e:
                            print(e)
                            
                
            except Exception as e:
                print(e)
    
        #print(self.es.indices.get_mapping('zilcrawl'))
            

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
                        if pool == self.token[tok].address0x or pool == self.token[tok].bech32_address:
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
        

crawler = zilcrawl()

