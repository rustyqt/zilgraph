#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 19:54:25 2020

@author: julian
"""

import time

from zilcrawl import zilcrawl
from zillog import zillog
from zilswap import zilswap

password = input("Enter password: ")

# zillog logs zilswap pool liquidity
zl = zillog(password)

# zilcrawl crawls for new blocks
crawl = zilcrawl(password)

# zilswap aggregates zilswap data
zwap = zilswap(password)

#zl.mrproper()
#crawl.mrproper()
#zwap.mrproper()

while True:
    zl.run()
    crawl.run()
    zwap.run()
    
    time.sleep(60)

