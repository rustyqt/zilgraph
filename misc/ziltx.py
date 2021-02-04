#!/usr/bin/python3.6

from pprint import pprint

from pyzil.zilliqa import chain
from pyzil.account import Account, BatchTransfer

from pyzil.zilliqa.api import ZilliqaAPI
from pyzil.zilliqa.chain import active_chain

import time


# Use MainNet
chain.set_active_chain(chain.MainNet)  

# Set API end-point to local seed node
active_chain.api = ZilliqaAPI("http://localhost:4201")


# Load main account from zilkey.txt
key_pair = []
with open('zilkey.txt', 'r') as fp:
    line = fp.readline()
    key_pair = line.strip().split()

account = Account(private_key=key_pair[1])
print("Account balance: {}".format(account.get_balance()))


# load additional accounts from zilkeys.txt
# This file contains multiple accounts - one account each line.
keys = []
with open('zilkeys.txt', 'r') as fp:
   line = fp.readline()
   cnt = 1
   while line:
       keys.append(line.strip().split())
       line = fp.readline()

accs = []

for key in keys:
    accs.append(Account(private_key=key[1]))




# Set to_addr to zilgraph.zil
to_addr = "zil1gwe43c3sjt3dxe7wmnggc5flmj3pvtqpl4awwc"

while True:
    print("---------------------------------------------------------------")
    for acc in accs:
    
        pprint(acc.bech32_address + " : " + str(acc.get_balance()) + " ZIL")
    
        batch = [BatchTransfer(to_addr=to_addr, zils=0) for ii in range(1000)]
        txn_info_list = acc.transfer_batch(batch, max_workers=200, timeout=120)
    
        time.sleep(10)
 
 
 

# Fund accounts with some ZILs from main account
 
#batch = [BatchTransfer(to_addr='zil14747autzr6jyfqp0tweu0xvfuk8pf7vn4ph55p', zils=200),
#         BatchTransfer(to_addr='zil1fa6j4jn76qhyk7fka7y3xxrms8gfan7jf3ak82', zils=200),
#         BatchTransfer(to_addr='zil150dy88jgcllgdevt49wwa98aajsqyssrgmwlnk', zils=200),
#         BatchTransfer(to_addr='zil1fs6sv6k0kxagel5z6xte8q0ueqm9yuv82wmnpe', zils=200),
#         BatchTransfer(to_addr='zil106dszpun2x73vtjtvg3q8dpk0xle48u37z0dpy', zils=200),
#         BatchTransfer(to_addr='zil1ntqajukc6r2kjvdtgk6wumu6ds966qwkf6fk9j', zils=200),
#         BatchTransfer(to_addr='zil1dnz8ghlw2dmhd7csa5ntgh42rzyxsujq8zd0np', zils=200),
#         BatchTransfer(to_addr='zil1nfhzwa8yn379dsa9gzmffd4y2fw8kkcukzfjt8', zils=200),
#         BatchTransfer(to_addr='zil146plghecnjgrw029x2xlzeqklclj8x6aqq7gzd', zils=200)]
#
#txn_info_list = account.transfer_batch(batch, max_workers=200, timeout=120)
#
#pprint(txn_info_list)


