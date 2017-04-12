# -*- coding: utf-8 -*-
import os

GIF_HTTP_FILES = [
    {
        'base_address': 'https://radar.weather.gov/ridge/Conus/RadarImg',
        'file_prefix': 'NAT',
        'frames_max': 144,
        'animation_speed': 10,
        'update_min': 15
    },
    {
        'base_address': 'https://radar.weather.gov/ridge/Conus/RadarImg',
        'file_prefix': 'southeast',
        'frames_max': 144,
        'animation_speed': 10,
        'update_min': 15
    },
    {
        'base_address': 'https://radar.weather.gov/ridge/Conus/RadarImg',
        'file_prefix': 'southmissvly',
        'frames_max': 144,
        'animation_speed': 10,
        'update_min': 15
    },
]

INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
LOG_PATH = os.path.join(INSTALL_DIRECTORY, 'status.log')
COMB_PATH = os.path.join(INSTALL_DIRECTORY, 'combined')
FRAME_PATH = os.path.join(INSTALL_DIRECTORY, 'frames')
