# -*- coding: utf-8 -*-
import os

# How often to download each GIF and look for new frames
PERIOD_MIN = 14

# How many frames does each GIF have
NUMBER_FRAMES = 9

# List of GIFs. Number of frames per GIF must be <= NUMBER_FRAMES
GIF_HTTP_FILES = [
    {
        'address': 'http://images.intellicast.com/WxImages/RadarLoop/usa_None_anim.gif',
        'frames_gif': 9,
        'frames_max': 96,
        'hash_size': 13
    },
    {
        'address': 'http://images.intellicast.com/WxImages/RadarLoop/csg_None_anim.gif',
        'frames_gif': 9,
        'frames_max': 96,
        'hash_size': 13
    }
]

INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
LOG_PATH = os.path.join(INSTALL_DIRECTORY, 'status.log')
COMB_PATH = os.path.join(INSTALL_DIRECTORY, 'combined')
FRAME_PATH = os.path.join(INSTALL_DIRECTORY, 'frames')
