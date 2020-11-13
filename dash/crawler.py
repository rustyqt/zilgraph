#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 19:54:25 2020

@author: julian
"""

import time

from zilcrawl import zilcrawl
from zillog import zillog

# Instantiate Zillogger
zl = zillog()

crawler = zilcrawl()
crawler.run()
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