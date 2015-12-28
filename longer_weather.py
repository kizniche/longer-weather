#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  longer_weather.py - Collect radar GIFs from intellicast.net and merge them together
#
#  Copyright (C) 2015  Kyle T. Gabriel
#
#  Mycodo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Mycodo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Mycodo. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at kylegabriel.com


#### Configure Directories ####
install_directory = "/home/user/longer-weather"

import getopt
import logging
import os
import subprocess
import sys
import time
import urllib
from datetime import datetime, timedelta
from threading import Timer

image_number = 0

log_path = "%s/log" % install_directory
daemon_log_file_tmp = "%s/daemon-tmp.log" % log_path

logging.basicConfig(
    filename = daemon_log_file_tmp,
    level = logging.INFO,
    format = '%(asctime)s [%(levelname)s] %(message)s')
    
logging.getLogger().setLevel(logging.INFO)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

#filename = link.split('/')[-1]
# Displays the program usage
def usage():
    print "lweather.py: Collect radar GIFs from intellicast.net and merge them together" \
        "\n"
    print "Usage:  lweather.py [OPTION]...\n"
    print "Options:"
    print "    -g, --generate"
    print "           Only generate animation from gifs in main directory"
    print "    -s, --sync Minutes [Start Number]"
    print "           Synchronize 2-hour intervals based on a 24-hour clock"
    print "           Enter only two-digits for Minutes (0-60)"
    print "           Optional: Enter a Start Number for file names"
    print "    -h, --help"
    print "           Display this help and exit\n"

# Check user options and arguments for validity
def menu():
    global image_number
    
    if len(sys.argv) == 1: # No arguments given
        daemon(0)
        sys.exit(1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'gs:n:h',
            ["generate", "number", "sync", "help"])
    except getopt.GetoptError as err:
        print(err) # will print "option -a not recognized"
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-g", "--generate"):
            logging.info("Generating large GIF animation")
            Combine_GIF()
            logging.info("GIF generation complete")
            sys.exit(0)
        elif opt in ("-s", "--sync"):
            if len(sys.argv) > 3:
                image_number = int(float(sys.argv[3]))
            daemon(int(float(sys.argv[2])))
            sys.exit(0)
        elif opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        else:
            assert False, "Fail"
            
def daemon(sync_minutes):
    global image_number
    future = datetime.now()
    
    logging.info("[Daemon] Daemon Started")
    
    if image_number > 0:
        logging.info("[Daemon] Starting image numbering at %s", image_number)
    
    # Synchronize to the correct time before beginning 2-hour interval timing
    if sync_minutes:
        future = future + timedelta(minutes = sync_minutes)
        logging.info("[Daemon] Sync: wait %s minutes, Start at %s", sync_minutes, future)
        while True:
            present = datetime.now()
            if present > future:
                break
            time.sleep(1.0)
    
    while True:
        image_number += 1

        #present = datetime.now()
        future = future + timedelta(hours = 2, minutes = 15)
        
        logging.info("[Daemon] Grabbing GIF #%s from intellicast.net", image_number)
        Get_GIF()
        
        logging.info("[Daemon] Combining individual GIFs into one large GIF animation")
        Combine_GIF()
        
        logging.info("[Daemon] Next Grab: %s", future)

        while True:
            present = datetime.now()
            if present > future:
                break
            time.sleep(1.0)
    
def Get_GIF():
    date_now = datetime.now().strftime("%Y%m%d%H%M%S")
    image_file = "%s/split/US-whole-%s-%s.gif" % (install_directory, date_now, image_number)
    urllib.urlretrieve(
        "http://images.intellicast.com/WxImages/RadarLoop/usa_None_anim.gif",
        image_file)

    logging.info("[Daemon] Changing last frame delay from 2.0 sec to 0.25 sec")
    gif_slice = "gifsicle -b %s -d25 \"#8\"" % image_file
    os.system(gif_slice)
    
def Combine_GIF():
    date_now = datetime.now().strftime("%Y%m%d%H%M%S")
    gifsicle = "gifsicle %s/split/*.gif > %s/combined/US-Combined-%s.gif" % (install_directory, install_directory, date_now)
    os.system(gifsicle)
    
menu()