# -*- coding: utf-8 -*-

from pprint import pprint

from pyzil.zilliqa import chain
from pyzil.zilliqa.units import Zil
from pyzil.zilliqa.api import ZilliqaAPI
from pyzil.account import Account

from pyzil.contract import Contract
from pyzil.zilliqa.chain import active_chain

import time
from datetime import datetime
import json

from elasticsearch import Elasticsearch

class pyzilly:

  def get_contract(self, contract_addr):
      contract = Contract.load_from_address(contract_addr)
      contract.get_state()
      pprint(contract.state)
      return contract
    
class zilswap:
    def __init__(self, password=""):
        # Set mainnet
        chain.set_active_chain(chain.MainNet)  
        
        # Set contract
        _addr = "zil1hgg7k77vpgpwj3av7q7vv5dl4uvunmqqjzpv2w"
        self.contract = Contract.load_from_address(_addr, load_state=True)
        
        # Set pyzil default API endpoint
        # active_chain.api = ZilliqaAPI("https://api.zilliqa.com/")
        active_chain.api = ZilliqaAPI("https://ssn.zillet.io/")
        # active_chain.api = ZilliqaAPI("http://localhost:4201")
        
        # Load Zilgraph JSON 
        fp_json = open("zilgraph.json")
        self.tokens = json.load(fp_json)["tokens"]
        
        # Setup dictionaries
        self.token = {}
        self.pools = {}
        self.decimals = {"zil" : 12}
        for tok in self.tokens:
            addr = self.tokens[tok]["addr"]
            self.token[tok]    = Account(address=addr)
            self.pools[Account(address=addr).bech32_address] = tok
            self.decimals[tok] = self.tokens[tok]["decimals"]
        
        self.es = Elasticsearch([{'host': 'localhost'}],http_auth=('elastic', password))
        

    def run(self):

        block_begin = 0
        try:
            query_body = {"aggs" : {"max_id" : {"max" : { "field" : "BlockNum"}}}, "size":0}
            res = self.es.search(index="zilswap", body=query_body, size=0)
            block_begin = int(res['aggregations']['max_id']['value'])
        except Exception as e:
            print(e)
            block_begin = 811030  # Zilswap Contract Creation
        
        block_end   = int(chain.active_chain.api.GetNumTxBlocks())
        
        #print("block_begin = " + str(block_begin))
        #print("block_end = " + str(block_end))
        
        for block_height in range(block_begin, block_end):
        
            query_body = {
                "query": {
                    "bool": {
                        "must": [
                            { "match": { "toAddr": "ba11eb7bcc0a02e947acf03cc651bfaf19c9ec00" } },
                            { "match": { "receipt.success": True } },
                            { "match": { "BlockNum": block_height } }
                            ]
                        }
                    }
                }
    
            
            res = self.es.search(index="zilcrawl", body=query_body, size=10000)
    
            swap = { }
            
            for hit in res['hits']['hits']:
                
                try:
                    data = json.loads(hit['_source']['data'])
                    events = json.loads(hit['_source']['receipt']['event_logs'])
                    transitions = json.loads(hit['_source']['receipt']['transitions'])
                    #pprint(events)
                    
                    swap = { }
                    
                    swap['ID']         = hit['_source']['ID']
                    swap['@timestamp'] = hit['_source']['@timestamp']
                    swap['timestamp']  = hit['_source']['timestamp']
                    swap['BlockNum']   = hit['_source']['BlockNum'] 
                    swap['tag'] = data['_tag']
                    
                    
                    if data['_tag'] == "SwapExactZILForTokens" or data['_tag'] == "SwapZILForExactTokens":
                        assert events[0]['params'][0]['vname'] == "pool"
                        assert events[0]['params'][1]['vname'] == "address"
                        assert events[0]['params'][2]['vname'] == "input"
                        assert events[0]['params'][3]['vname'] == "output"
                        
                        swap['pool0x'] = Account(address=events[0]['params'][0]['value']).address0x
                        swap['pool']   = Account(address=events[0]['params'][0]['value']).bech32_address
                        swap['addr0x'] = Account(address=events[0]['params'][1]['value']).address0x
                        swap['addr']   = Account(address=events[0]['params'][1]['value']).bech32_address
                        
                        if swap['pool'] in self.pools:
                            swap['name']  = self.pools[swap['pool']]
                            swap['zil']   = int(events[0]['params'][2]['value']['arguments'][1])*pow(10,-self.decimals['zil'])
                            swap['tok']   = int(events[0]['params'][3]['value']['arguments'][1])*pow(10,-self.decimals[self.pools[swap['pool']]])
                            swap['rate']  = swap['zil'] / swap['tok']
                            swap['apy'] = self.get_apy(swap['name'])
        
                    if data['_tag'] == "SwapExactTokensForZIL" or data['_tag'] == "SwapTokensForExactZIL":
                        assert events[0]['params'][0]['vname'] == "pool"
                        assert events[0]['params'][1]['vname'] == "address"
                        assert events[0]['params'][2]['vname'] == "input"
                        assert events[0]['params'][3]['vname'] == "output"
                        
                        swap['pool0x'] = Account(address=events[0]['params'][0]['value']).address0x
                        swap['pool']   = Account(address=events[0]['params'][0]['value']).bech32_address
                        swap['addr0x'] = Account(address=events[0]['params'][1]['value']).address0x
                        swap['addr']   = Account(address=events[0]['params'][1]['value']).bech32_address
                        
                        if swap['pool'] in self.pools:
                            swap['name']  = self.pools[swap['pool']]
                            swap['tok']   = int(events[0]['params'][2]['value']['arguments'][1])*pow(10,-self.decimals[self.pools[swap['pool']]])
                            swap['zil']   = int(events[0]['params'][3]['value']['arguments'][1])*pow(10,-self.decimals['zil'])
                            swap['rate']  = swap['zil'] / swap['tok']
                            swap['apy'] = self.get_apy(swap['name'])
                    
                    if data['_tag'] == "AddLiquidity":
                        #pprint(events)
                        #pprint(transitions)
                        
                        assert events[0]['params'][0]['vname'] == "pool"
                        assert events[0]['params'][1]['vname'] == "address"
                        assert events[0]['params'][2]['vname'] == "amount"
                        assert events[0]['_eventname'] == 'Mint'
                        assert events[1]['_eventname'] == 'TransferFromSuccess'
                        
                        swap['pool0x'] = Account(address=events[0]['params'][0]['value']).address0x
                        swap['pool']   = Account(address=events[0]['params'][0]['value']).bech32_address
                        swap['addr0x'] = Account(address=events[0]['params'][1]['value']).address0x
                        swap['addr']   = Account(address=events[0]['params'][1]['value']).bech32_address
                                            
                        if swap['pool'] in self.pools:
                            swap['name'] = self.pools[swap['pool']]
                            swap['zil_liq']  = int(hit['_source']['amount'])*pow(10,-self.decimals['zil'])                            
                            swap['tok_liq']  = int(events[1]['params'][3]['value'])*pow(10,-self.decimals[self.pools[swap['pool']]])                            
                            swap['rate'] = swap['zil_liq'] / swap['tok_liq']
                            
                            if transitions[2]['msg']['params'][3]['vname'] == "new_to_bal":                            
                                swap['liquidity_tok'] = int(transitions[2]['msg']['params'][3]['value'])*pow(10,-self.decimals[self.pools[swap['pool']]])
                                swap['liquidity_zil'] = swap['liquidity_tok'] * swap['rate']
                        
                        #pprint(swap)
                        
                    if data['_tag'] == "RemoveLiquidity":
                        #pprint(events)
                        #pprint(swap)
                        
                        assert events[0]['params'][0]['vname'] == "pool"
                        assert events[0]['params'][1]['vname'] == "address"
                        assert events[0]['params'][2]['vname'] == "amount"
                        assert events[0]['_eventname'] == 'Burnt'
                        assert events[1]['_eventname'] == 'TransferSuccess'
                        assert transitions[0]['msg']['_tag'] == 'AddFunds'
                        
                        swap['pool0x'] = Account(address=events[0]['params'][0]['value']).address0x
                        swap['pool']   = Account(address=events[0]['params'][0]['value']).bech32_address
                        swap['addr0x'] = Account(address=events[0]['params'][1]['value']).address0x
                        swap['addr']   = Account(address=events[0]['params'][1]['value']).bech32_address
                        
                        if swap['pool'] in self.pools:
                            swap['name']  = self.pools[swap['pool']]
                            swap['zil_liq']  = int(transitions[0]['msg']['_amount'])*pow(10,-self.decimals['zil'])
                            swap['tok_liq'] = int(events[1]['params'][2]['value'])*pow(10,-self.decimals[self.pools[swap['pool']]])
                            swap['rate'] = swap['zil_liq'] / swap['tok_liq']
                            
                            
                            
                    pprint(swap)
                    self.es.create("zilswap", swap['ID'], swap, ignore=[409])
                
                except Exception as e:
                    print(e)
                    pprint(swap)
                    
                    
    
        
    def get_market(self, tokenstr):        
        _time = int(time.time())
        self.contract.get_state()
        _poolsize = self.contract.state['pools'][self.token[tokenstr].address0x]['arguments']
        
        _liq_zil = int(_poolsize[0])*1e-12
        _liq_token = int(_poolsize[1])*pow(10,-self.decimals[tokenstr])
        _rate = _liq_zil / _liq_token
        
        _market_data_point = {"_id": _time,
                              "rate": _rate,
                              "liq_zil": _liq_zil,
                              "liq_"+tokenstr: _liq_token}
        
        return _market_data_point
    
    def get_state(self, tokenstr):        
        self.contract.get_state()
        _poolsize = self.contract.state['pools'][self.token[tokenstr].address0x]['arguments']
        
        zil_liq = int(_poolsize[0])*1e-12
        tok_liq = int(_poolsize[1])*pow(10,-self.decimals[tokenstr])
        rate = zil_liq / tok_liq
        
        _market_data_point = {"name": tokenstr,
                              "rate": rate,
                              "zil_liq": zil_liq,
                              "tok_liq": tok_liq}
        
        return _market_data_point
    
    def get_volume(self, tokenstr):
        
        # Query monthly volume
        query = {
          "aggs": {
            "1": {
              "sum": {
                "field": "zil"
              }
            }
          },
          "size": 0,
          "stored_fields": [
            "*"
          ],
          "script_fields": {},
          "docvalue_fields": [
            {
              "field": "@timestamp",
              "format": "date_time"
            }
          ],
          "_source": {
            "excludes": []
          },
          "query": {
            "bool": {
              "must": [],
              "filter": [
                {
                  "match_all": {}
                },
                {
                  "match_phrase": {
                    "name.keyword": tokenstr
                  }
                },
                {
                  "range": {
                    "@timestamp": {
                      "gte": datetime.fromtimestamp(int(time.time()-30.42*24*3600)).isoformat(),
                      "lte": datetime.fromtimestamp(int(time.time())).isoformat(),
                      "format": "strict_date_optional_time"
                    }
                  }
                }
              ],
              "should": [],
              "must_not": []
            }
          }
        }

        res = self.es.search(index="zilswap", body=query, size=0)
        return res['aggregations']['1']['value']
        
    def get_apy(self, tokenstr):
        
        # Get Volume
        volume = self.get_volume(tokenstr)
        self.contract.get_state()
        poolsize = self.contract.state['pools'][self.token[tokenstr].address0x]['arguments']
        
        # Get Liquiditiy
        liq_zil = int(poolsize[0])*1e-12
        
        # Set Fees
        fees = 0.003
        
        apy = 12*volume*fees/(2*liq_zil)
        
        return apy
    
    def mrproper(self):
        # Delete existing zilswap index
        self.es.indices.delete(index='zilswap', ignore=[400, 404])
            
