#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  longer_weather.py - Collect radar GIFs from intellicast.net and
#                      merge them together
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
#
#  Prerequisites: pillow tesseract imagehash imageio
#  8 new frames are generated roughly every 2 hours 15 minutes
#
import argparse
import logging
import grp
import imagehash
import imageio
import os
import pwd
import sys
import time
import urllib
from PIL import Image
from datetime import datetime
from datetime import timedelta
from shutil import copyfile
from threading import Thread

REF_PERIOD_MIN = 16
GIF_HTTP_FILES = [
    'http://images.intellicast.com/WxImages/RadarLoop/usa_None_anim.gif',
    'http://images.intellicast.com/WxImages/RadarLoop/csg_None_anim.gif'
]

INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
LOG_PATH = os.path.join(INSTALL_DIRECTORY, 'status.log')
COMB_PATH = os.path.join(INSTALL_DIRECTORY, 'combined')
FRAME_PATH = os.path.join(INSTALL_DIRECTORY, 'frames')

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
    """Longer Weather Class"""
    def __init__(self):
        Thread.__init__(self)
        self.frame_number = {}
        self.last_img_sizes = {}
        for each_gif in GIF_HTTP_FILES:
            file_name = each_gif.split('/')[-1][:-4]
            self.frame_number[file_name] = 1
            self.last_img_sizes[file_name] = []
        self.start_time = datetime.now()
        self.timer = datetime.now()
        self.running = True

    def run(self):
        logger.info("[Daemon] Daemon Started")

        while self.running:
            present = datetime.now()
            if present > self.timer:
                self.timer = self.timer + timedelta(minutes=REF_PERIOD_MIN)
                for each_gif in GIF_HTTP_FILES:
                    gif_name = each_gif.split('/')[-1][:-4]
                    logger.info("[Daemon] Saving GIF from intellicast.net")
                    gif_image_file = self.get_gif(each_gif)
                    logger.info("[Daemon] GIF acquired, extracting frames")
                    self.process_image(gif_image_file, gif_name)
                    logger.info("[Daemon] Deleting GIF")
                    os.remove(gif_image_file)
                    logger.info("[Daemon] Creating combined GIF")
                    self.combine_gif(gif_name)
                logger.info("[Daemon] Next Grab: {next:.2f} minutes".format(
                    next=(self.timer - present).total_seconds() / 60))
            time.sleep(1)

    @staticmethod
    def get_gif(gif_address):
        date_now = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        gif_image_file = "{path}/frames/{date}-{name}.gif".format(
            path=INSTALL_DIRECTORY, date=date_now, name=gif_address.split('/')[-1][:-4])
        urllib.urlretrieve(gif_address, gif_image_file)
        return gif_image_file

    def combine_gif(self, gif_name):
        save_path = '{path}/combined/{date}-{name}.gif'.format(
            path=INSTALL_DIRECTORY,
            date=self.start_time.strftime("%Y_%m_%d_%H-%M-%S"),
            name=gif_name)
        images = []
        for dir_name, _, file_names in os.walk(FRAME_PATH):
            for each_name in sorted(file_names):
                if gif_name in each_name:
                    images.append(imageio.imread(os.path.join(dir_name, each_name)))
        imageio.mimsave(save_path, images)

    def terminate(self):
        self.running = False

    @staticmethod
    def analyze_image(path):
        """
        Pre-process pass over the image to determine the mode (full or additive).
        Necessary as assessing single frames isn't reliable. Need to know the mode 
        before processing all frames.
        """
        im = Image.open(path)
        results = {
            'size': im.size,
            'mode': 'full',
        }
        try:
            while True:
                if im.tile:
                    tile = im.tile[0]
                    update_region = tile[1]
                    update_region_dimensions = update_region[2:]
                    if update_region_dimensions != im.size:
                        results['mode'] = 'partial'
                        break
                im.seek(im.tell() + 1)
        except EOFError:
            pass
        return results

    def process_image(self, img_path, gif_name):
        """ Iterate the GIF, extracting each frame """
        mode = self.analyze_image(img_path)['mode']
        im = Image.open(img_path)
        i = 0
        p = im.getpalette()

        try:
            while True:
                logger.debug('saving {path} ({mode}) frame {frame}, {size} {title}'.format(
                    path=img_path, mode=mode, frame=i, size=im.size, title=im.tile))

                # If the GIF uses local colour tables, each frame will have its own palette
                # If not, we need to apply the global palette to the new frame
                if not im.getpalette():
                    im.putpalette(p)

                new_frame = Image.new('RGBA', im.size)
                new_frame.paste(im, (0, 0), im.convert('RGBA'))

                # Save frame to file
                check_frame_path = '{path}/check_frame.png'.format(path=FRAME_PATH)
                new_frame.save(check_frame_path, 'PNG')

                # hash frame image and compare hash to last hashed frames.
                # If hash is unique, it's a new frame. Save it as a new file.
                img_hash = imagehash.dhash(Image.open(check_frame_path), hash_size=12)
                if str(img_hash) not in self.last_img_sizes[gif_name]:
                    self.last_img_sizes[gif_name].append(str(img_hash))
                    logger.info("Hashes: {}".format(self.last_img_sizes))
                    frame_name = '{name}-{frame:0>5}.png'.format(
                        name=gif_name, frame=self.frame_number[gif_name])
                    new_file = os.path.join(FRAME_PATH, frame_name)
                    copyfile(check_frame_path, new_file)
                    self.frame_number[gif_name] += 1

                os.remove(check_frame_path)
                i += 1
                im.seek(im.tell() + 1)

                # Ensure the list stays relatively small
                if len(self.last_img_sizes[gif_name]) > 16:
                    self.last_img_sizes[gif_name].pop(0)
        except EOFError:
            pass


def assure_path_exists(dir_path):
    """ Create path if it doesn't exist """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        os.chmod(dir_path, 0774)
        # set_user_grp(dir_path, 'mycodo', 'mycodo')
    return dir_path


def set_user_grp(file_path, user, group):
    """ Set the UID and GUID of a file """
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.chown(file_path, uid, gid)


def delete_all_gifs(dir_path):
    file_list = [f for f in os.listdir(dir_path) if f.endswith(".gif") or f.endswith(".png")]
    for f in file_list:
        file_del = os.path.join(dir_path, f)
        os.remove(file_del)


def parseargs(parse):
    parse.add_argument('-d', '--dontdelete', action='store_true',
                       help="Don't delete the images already in sync/")
    return parse.parse_args()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Longer Weather")
    args = parseargs(parser)
    assure_path_exists(COMB_PATH)
    assure_path_exists(FRAME_PATH)

    logger.debug('Deleting gifs')
    delete_all_gifs(FRAME_PATH)

    longer_weather = LongerWeather()
    longer_weather.start()
    try:
        while longer_weather.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error("Keyboard exit")
        longer_weather.terminate()
        sys.exit(1)
