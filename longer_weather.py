#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  longer_weather.py - Collect GIFs, split into frames, collect frames, then
#                      merge them together to create one long animation.
#                      Originally used to create long weather radar animations
#                      but may work with other hosted GIFs.
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
#
#  Raspberry Pi:
#    sudo apt-get install python-numpy imagemagick
#    sudo pip install pillow imagehash
#
import argparse
import hashlib
import imagehash
import logging
import os
import subprocess
import sys
import time
import urllib
from PIL import Image
from datetime import datetime
from datetime import timedelta
from threading import Thread
from config import GIF_HTTP_FILES
from config import LOG_PATH
from config import FRAME_PATH

logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

fileHandler = logging.FileHandler(LOG_PATH)
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

logger.setLevel(logging.INFO)


class LongerWeather(Thread):
    """Longer Weather"""
    def __init__(self):
        Thread.__init__(self)
        logger.info('Daemon Started')
        self.start_time = datetime.now()
        self.timer = {}
        self.file_time = {}
        for gif_address in GIF_HTTP_FILES:
            self.timer[gif_address['file_prefix']] = datetime.now()
            self.file_time[gif_address['file_prefix']] = (
                datetime.utcnow().replace(minute=8) - timedelta(hours=4))
        self.running = True

    def run(self):
        while self.running:
            present = datetime.now()

            # Download and save the original GIFs
            for gif_address in GIF_HTTP_FILES:
                unique_name = '{base}_{prefix}'.format(
                    base=gif_address['base_address'].split('/')[-1],
                    prefix=gif_address['file_prefix'])
                path_frames = os.path.join(FRAME_PATH, unique_name)
                assure_path_exists(path_frames)

                if present > self.timer[gif_address['file_prefix']]:
                    self.timer[gif_address['file_prefix']] += timedelta(minutes=gif_address['update_min'])

                    frame_good = True
                    new_frames = False

                    while frame_good:

                        filename = self.file_time[gif_address['file_prefix']].strftime(
                            '{prefix}_%Y%m%d_%H%M.gif'.format(
                                prefix=gif_address['file_prefix']))
                        save_file = os.path.join(path_frames, filename)

                        dl_address = '{address}/{filename}'.format(
                            address=gif_address['base_address'],
                            filename=filename)

                        if self.get_gif(dl_address, save_file):
                            new_frames = True
                            self.file_time[gif_address['file_prefix']] += timedelta(minutes=10)
                        else:
                            frame_good = False

                    if new_frames:
                        # Create GIF from frames
                        gif_save = os.path.join(
                            FRAME_PATH, '{name}.gif'.format(name=unique_name))
                        self.create_gif(path_frames, gif_save, gif_address)

                        # Create webm from GIF
                        # webm_save = os.path.join(
                        #     FRAME_PATH, '{name}.webm'.format(name=name_root))
                        # self.create_webm(gif_save, webm_save)

                    logger.info('Next Grab: {next:.2f} minutes'.format(
                        next=(self.timer[gif_address['file_prefix']] - present).total_seconds() / 60))

            time.sleep(1)

    @staticmethod
    def create_gif(path_frames, gif_save, gif_settings):
        """ Use images in each frames subdirectory to create a GIF """
        # Delete any frames greater than the max limit
        files_all = sorted(next(os.walk(path_frames))[2])
        while len(files_all) > gif_settings['frames_max']:
            os.remove(os.path.join(path_frames, files_all[0]))
            files_all = sorted(next(os.walk(path_frames))[2])

        logger.info('Generating {f}'.format(f=gif_save))
        logger.info('from {f}/*.png'.format(f=path_frames))

        cmd = "ffmpeg -y -framerate {frate} -pattern_type glob -i '{path}/*.png' {gif}".format(
                frate=gif_settings['animation_speed'],
                path=path_frames,
                gif=gif_save)
        logger.info('CMD: {f}'.format(f=cmd))
        subprocess.call(cmd, shell=True)

        # cmd = 'convert {gif} -fuzz 10% -layers Optimize {gif}.opt.gif'.format(
        #     gif=gif_save)
        # logger.info('CMD: {f}'.format(f=cmd))
        # subprocess.call(cmd, shell=True)

        # cmd = 'gifsicle -O3 {gif} -o {gif}.opt.gif'.format(
        #     gif=gif_save)
        # logger.info('CMD: {f}'.format(f=cmd))
        # subprocess.call(cmd, shell=True)

        # cmd = "ffmpeg -y -framerate 10 -pattern_type glob -i '{path}/*.png' -f image2pipe -vcodec ppm - | " \
        #       "convert -layers Optimize - {gif}".format(
        #         path=path_frames,
        #         gif=gif_save)
        # logger.info('CMD: {f}'.format(f=cmd))
        # subprocess.call(cmd, shell=True)

        # last_file = sorted(next(os.walk(path_frames))[2])[-1]
        # cmd = 'convert -delay 10 -loop 0 {path}/*.gif -delay 200 {path}/{last_file} {gif}'.format(
        #         path=path_frames,
        #         last_file=last_file,
        #         gif=gif_save)

        # Get last file to pause GIF
        # last_file = os.path.join(
        #     gif['path_frames'],
        #     sorted(next(os.walk(gif['path_frames']))[2])[-1])
        # cmd = 'convert -delay {speed} {path}/*.png -delay 200 {last} -loop 0 {spath}'.format(
        #     speed=gif_settings['animation_speed'],
        #     path=gif['path_frames'],
        #     last=last_file,
        #     spath=gif['new_gif'])
        # logger.info('CMD: {f}'.format(f=cmd))
        # subprocess.call(cmd, shell=True)

    @staticmethod
    def create_webm(gif_save, webm_save):
        logger.info("Creating {webm}".format(webm=webm_save))
        cmd = 'ffmpeg -y -i {gif}.opt.gif -c:v libvpx -crf 50 -b:v 256K -auto-alt-ref 0 {webm}'.format(
            gif=gif_save,
            webm=webm_save)
        logger.info('CMD: {f}'.format(f=cmd))
        subprocess.call(cmd, shell=True)

    @staticmethod
    def get_gif(gif_address, gif_saved):
        """ Download a GIF """
        logger.info('Get {f}'.format(f=gif_address))
        urllib.urlretrieve(gif_address, gif_saved)
        logger.info('Saved {f}'.format(f=gif_saved))
        if '404 Not Found' in open(gif_saved).read():
            os.remove(gif_saved)
            return False

        file_png = '{name}.png'.format(name=gif_saved.split('.')[0])

        cmd = 'convert {gif} {png}'.format(
            gif=gif_saved,
            png=file_png)
        logger.info('CMD: {f}'.format(f=cmd))
        subprocess.call(cmd, shell=True)

        os.remove(gif_saved)

        cmd = 'pngquant --quality 2-10 64 {png}'.format(
            png=file_png)
        logger.info('CMD: {f}'.format(f=cmd))
        subprocess.call(cmd, shell=True)

        os.remove(file_png)

        return True

    @staticmethod
    def hash_generate(frame, size):
        return str(imagehash.dhash(Image.open(frame), hash_size=size))

    @staticmethod
    def remove_duplicates(dir):
        unique = []
        root_path, _, file_names = next(os.walk(dir))
        for filename in sorted(file_names):
            file_path = os.path.join(root_path, filename)
            if os.path.isfile(file_path):
                filehash = hashlib.md5(file(file_path).read()).hexdigest()
                if filehash not in unique:
                    unique.append(filehash)
                else:
                    os.remove(file_path)

    def terminate(self):
        self.running = False


def assure_path_exists(dir_path):
    """ Create path if it doesn't exist """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        os.chmod(dir_path, 0774)
    return dir_path


def delete_images(dir_path):
    """ Delete all GIFs and PNGs in """
    file_list = [f for f in os.listdir(dir_path) if f.endswith('.gif') or f.endswith('.png')]
    for f in file_list:
        file_del = os.path.join(dir_path, f)
        os.remove(file_del)


def parseargs(parse):
    parse.add_argument('-d', '--delete', action='store_true',
                       help='Delete all current images')
    return parse.parse_args()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Longer Weather')
    args = parseargs(parser)

    if args.delete:
        for dir_name, dir_names, file_names in os.walk(FRAME_PATH):
            for each_directory in dir_names:
                path = os.path.join(dir_name, each_directory)
                logger.info('Deleting {f}'.format(f=path))
                delete_images(path)

    longer_weather = LongerWeather()
    longer_weather.daemon = True
    longer_weather.start()
    try:
        while longer_weather.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error('Keyboard exit')
        longer_weather.terminate()
        sys.exit(1)
