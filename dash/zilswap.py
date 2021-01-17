# -*- coding: utf-8 -*-

from pprint import pprint

from pyzil.zilliqa import chain
from pyzil.zilliqa.units import Zil
from pyzil.zilliqa.api import ZilliqaAPI
from pyzil.account import Account

from pyzil.contract import Contract
from pyzil.zilliqa.chain import active_chain

import time
import json

from elasticsearch import Elasticsearch

class pyzilly:

  def get_contract(self, contract_addr):
      contract = Contract.load_from_address(contract_addr)
      contract.get_state()
      pprint(contract.state)    
      return contract
    
class zilswap:
    def __init__(self):
        # Set mainnet
        chain.set_active_chain(chain.MainNet)  
        
        # Set contract
        _addr = "zil1hgg7k77vpgpwj3av7q7vv5dl4uvunmqqjzpv2w"
        self.contract = Contract.load_from_address(_addr, load_state=True)
        
        # Set Zilliqa API
        self.api = ZilliqaAPI("https://api.zilliqa.com/")
        
        # Set pyzil default API endpoint
        # active_chain.api = ZilliqaAPI("https://ssn.zillet.io/")
        
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
            self.pools[Account(address=addr).address0x]   = tok
            self.decimals[tok] = self.tokens[tok]["decimals"]
            
            
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        { "match": { "toAddr": "ba11eb7bcc0a02e947acf03cc651bfaf19c9ec00" } },
                        { "match": { "receipt.success": True } },
                        #{ "match": { "data": "*SwapExactZILForTokens*" } },
                        #{ "match": { "data": "*SwapExactTokensForZIL*" } },
                        #{ "match": { "data": "*SwapZILForExactTokens*" } },
                        #{ "match": { "data": "*SwapTokensForExactZIL*" } },
                        #{ "match": { "data": "*SwapExactTokensForTokens*" } },
                        #{ "match": { "data": "*SwapTokensForExactTokens*" } },
                        #{ "match": { "data": "*AddLiquidity*" } },
                        #{ "match": { "data": "*RemoveLiquidity*" } }
                        ]
                    }
                }
            }



        self.es = Elasticsearch([{'host': '192.168.188.32'}])
        res = self.es.search(index="zilcrawl", body=query_body, size=10000)

        # Delete existing zilswap index
        self.es.indices.delete(index='zilswap', ignore=[400, 404])
        
        swap = { }
        
        for hit in res['hits']['hits']:
            
            data = json.loads(hit['_source']['data'])
            events = json.loads(hit['_source']['receipt']['event_logs'])
            
            #pprint(data)
            #pprint(events)
            
            swap = { }
            
            swap['ID'] = hit['_source']['ID']
            swap['@timestamp'] = hit['_source']['@timestamp']
            swap['timestamp'] =hit['_source']['timestamp']
            swap['tag'] = data['_tag']
            
            if data['_tag'] == "SwapExactZILForTokens" or data['_tag'] == "SwapZILForExactTokens":
                assert events[0]['params'][0]['vname'] == "pool"
                assert events[0]['params'][1]['vname'] == "address"
                assert events[0]['params'][2]['vname'] == "input"
                assert events[0]['params'][3]['vname'] == "output"
                
                swap['pool'] = events[0]['params'][0]['value']
                swap['addr'] = events[0]['params'][1]['value']
                
                if swap['pool'] in self.pools:
                    swap['name']  = self.pools[swap['pool']]
                    swap['zil']   = int(events[0]['params'][2]['value']['arguments'][1])*pow(10,-self.decimals['zil'])
                    swap['tok']   = int(events[0]['params'][3]['value']['arguments'][1])*pow(10,-self.decimals[self.pools[swap['pool']]])
                    swap['rate']  = swap['zil'] / swap['tok']
                

            if data['_tag'] == "SwapExactTokensForZIL" or data['_tag'] == "SwapTokensForExactZIL":
                assert events[0]['params'][0]['vname'] == "pool"
                assert events[0]['params'][1]['vname'] == "address"
                assert events[0]['params'][2]['vname'] == "input"
                assert events[0]['params'][3]['vname'] == "output"
                
                swap['pool'] = events[0]['params'][0]['value']
                swap['addr'] = events[0]['params'][1]['value']
                
                if swap['pool'] in self.pools:
                    swap['name']  = self.pools[swap['pool']]
                    swap['tok']   = int(events[0]['params'][2]['value']['arguments'][1])*pow(10,-self.decimals[self.pools[swap['pool']]])
                    swap['zil']   = int(events[0]['params'][3]['value']['arguments'][1])*pow(10,-self.decimals['zil'])
                    swap['rate']  = swap['zil'] / swap['tok']
                
            
            
            pprint(swap)
            
            
            self.es.create("zilswap", swap['ID'], swap, ignore=[409])

    
        
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


swap = zilswap()