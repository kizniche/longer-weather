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
#  Raspberry Pi:
#    sudo apt-get install python-numpy imagemagick
#    sudo pip install pillow imagehash
#
import argparse
import filecmp
import grp
import imagehash
import logging
import os
import pwd
import subprocess
import sys
import time
import urllib
from PIL import Image
from datetime import datetime
from datetime import timedelta
from random import randint
from shutil import copyfile
from threading import Thread
from config import PERIOD_MIN
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
        self.frame_number = {}
        self.frame_hashes = {}
        self.startup = {}
        for gif_address in GIF_HTTP_FILES:
            gif = self.return_paths(gif_address['address'])
            self.frame_number[gif['name_root']] = 1
            self.frame_hashes[gif['name_root']] = []
            self.startup[gif['name_root']] = True
        self.timer = datetime.now()
        self.hash_table_populate()  # Populate hash table if frames exist
        self.running = True

    def run(self):
        while self.running:
            present = datetime.now()
            if present > self.timer:
                
                self.timer = self.timer + timedelta(minutes=PERIOD_MIN)

                # Download and save the original GIFs
                for gif_address in GIF_HTTP_FILES:
                    gif = self.return_paths(gif_address['address'])
                    if self.get_gif(gif_address['address'], gif['gif_saved']):
                        gif = self.return_paths(gif_address['address'])
                        # Separate and save unique frames from the GIF
                        self.gif_to_frames(gif, gif_address)

                        # Delete the original GIF
                        logger.info('Deleting {f}'.format(f=gif['gif_saved']))
                        os.remove(gif['gif_saved'])

                        # Create new GIF from unique frames
                        self.create_gif(gif, gif_address['frames_max'])
                
                logger.info('Next Grab: {next:.2f} minutes'.format(
                    next=(self.timer - present).total_seconds() / 60))

            time.sleep(1)

    @staticmethod
    def create_gif(gif, frames_max):
        """ Use images in each frames subdirectory to create a GIF """
        # Delete any frames greater than the max limit
        files_all = sorted(next(os.walk(gif['path_frames']))[2])
        while len(files_all) > frames_max:
            os.remove(files_all[0])
            files_all = sorted(next(os.walk(gif['path_frames']))[2])

        # Get last file to pause GIF
        last_file = os.path.join(
            gif['path_frames'],
            sorted(next(os.walk(gif['path_frames']))[2])[-1])
        logger.info('Generating {f}'.format(f=gif['new_gif']))
        logger.info('from {f}/*.png'.format(f=gif['path_frames']))
        cmd = 'convert -delay 10 {path}/*.png -delay 200 {last} -loop 0 {spath}'.format(
            path=gif['path_frames'],
            last=last_file,
            spath=gif['new_gif'])
        logger.info('CMD: {f}'.format(f=cmd))
        subprocess.call(cmd, shell=True)

    @staticmethod
    def get_gif(gif_address, gif_saved):
        """ Download a GIF """
        file_first = None
        file_second = None
        file_third = None
        success = False
        max_tries = 3
        tries = 0
        logger.info('Get {f}'.format(f=gif_address))

        # Occasionally the GIF server will render a GIF of an incorrect time
        # period or sequence. Therefore, we download it a few times and
        # compare them.
        while tries < max_tries:
            file_first = '{}-first.gif'.format(gif_saved)
            logger.info('Download {f}'.format(f=file_first.split('/')[-1]))
            urllib.urlretrieve(gif_address, file_first)
            time.sleep(randint(2, 10))
            file_second = '{}-second.gif'.format(gif_saved)
            logger.info('Download {f}'.format(f=file_second.split('/')[-1]))
            urllib.urlretrieve(gif_address, file_second)
            time.sleep(randint(2, 10))
            file_third = '{}-third.gif'.format(gif_saved)
            logger.info('Download {f}'.format(f=file_third.split('/')[-1]))
            urllib.urlretrieve(gif_address, file_third)
            if (filecmp.cmp(file_first, file_second) and
                    filecmp.cmp(file_second, file_third)):
                copyfile(file_first, gif_saved)
                logger.info('Downloaded GIFs are the same')
                success = True
                tries = 4
            else:
                logger.error('Downloaded GIFs are not the same! Wait 20 sec.')
                time.sleep(20)
            tries += 1

        if not success:
            return False

        os.remove(file_first)
        os.remove(file_second)
        os.remove(file_third)
        logger.info('Saved {f}'.format(f=gif_saved))
        return True

    def gif_to_frames(self, gif, gif_config):
        """ Iterate the GIF, extracting each frame """
        if not os.path.isfile(gif['gif_saved']):
            logger.error('No File {f}'.format(f=gif['gif_saved']))
            return

        im = Image.open(gif['gif_saved'])
        i = 0
        p = im.getpalette()
        gif_check = False
        max_tries = 3
        tries = 0
        logger.info('Extracting frames from {f}'.format(
            f=gif['gif_saved'].split('/')[-1]))

        try:
            while True:
                logger.debug('Frame {i}: {path}, {size}, {title}'.format(
                    i=i, path=gif['gif_saved'], size=im.size, title=im.tile))

                # If the GIF uses local colour tables, each frame will have
                # its own palette. If not, we need to apply the global palette
                # to the new frame.
                if not im.getpalette():
                    im.putpalette(p)

                new_frame = Image.new('RGBA', im.size)
                new_frame.paste(im, (0, 0), im.convert('RGBA'))

                # Save frame to file
                path_frame_tmp = os.path.join(gif['path_frames'], 'frame.png')
                new_frame.save(path_frame_tmp, 'PNG')

                # hash frame image and compare hash to last hashed frames.
                # If hash is unique, it's a new frame. Save it as a new file.
                img_hash = self.hash_generate(
                    path_frame_tmp, gif_config['hash_size'])

                # Check if the first frame is in the hash list (it should)
                # If it isn't, the GIF may be of an erroneous time period
                # (sporadically happens with this server)
                if not self.startup[gif['name_root']]:
                    while not gif_check and tries < max_tries:
                        if img_hash not in self.frame_hashes[gif['name_root']]:
                            logger.error('First frame of new GIF not '
                                         'found in the previous GIF!')
                            logger.error('Redownloading GIF.')
                            self.get_gif(
                                gif_config['address'], gif['gif_saved'])
                            tries += 1
                        else:
                            logger.info('First frame of GIF found in hash '
                                        'list (Good)')
                            gif_check = True

                permit_hash_check = ((gif_check or tries > max_tries) or
                                     self.startup[gif['name_root']])

                if (permit_hash_check and
                        img_hash not in self.frame_hashes[gif['name_root']]):
                    frame_name = '{name}-{frame:0>5}.png'.format(
                        name=gif['name'],
                        frame=self.frame_number[gif['name_root']])
                    path_frame_copy = os.path.join(
                        gif['path_frames'], frame_name)
                    copyfile(path_frame_tmp, path_frame_copy)

                    logger.info('New {file} hash {hash}'.format(
                        file=frame_name, hash=img_hash))
                    logger.debug('Hashes: {}'.format(
                        self.frame_hashes[gif['name_root']]))

                    self.frame_hashes[gif['name_root']].append(img_hash)
                    self.frame_number[gif['name_root']] += 1

                self.hash_table_trim(
                    gif['name_root'], gif_config['frames_gif'])

                os.remove(path_frame_tmp)
                i += 1
                im.seek(im.tell() + 1)
        except EOFError:
            pass

        self.startup[gif['name_root']] = False

    @staticmethod
    def hash_generate(frame, size):
        return str(imagehash.dhash(Image.open(frame),hash_size=size))

    def hash_table_populate(self):
        """ If frames exist, populate the hash table with their hashes """
        for gif_address in GIF_HTTP_FILES:
            gif = self.return_paths(gif_address['address'])
            all_files = sorted(next(os.walk(gif['path_frames']))[2])
            for each_file in all_files:
                name_test = '{name}-'.format(name=gif['name'])
                if name_test in each_file.split('/')[-1]:
                    file_path = os.path.join(gif['path_frames'], each_file)
                    file_hash = self.hash_generate(
                        file_path, gif_address['hash_size'])
                    logger.info('Found {file}, {hash}'.format(
                        file=each_file,
                        hash=file_hash
                    ))
                    self.frame_hashes[gif['name_root']].append(file_hash)
                    self.frame_number[gif['name_root']] += 1

            self.hash_table_trim(gif['name_root'], gif_address['frames_gif'])

    def hash_table_trim(self, name_root, frames_gif):
        """ Trim hash table to certain length """
        # Ensure the list stays close but not smaller than the number of
        # frames in the original GIF.
        while len(self.frame_hashes[name_root]) > frames_gif + 1:
            self.frame_hashes[name_root].pop(0)

    def return_paths(self, http_address):
        """ Return path and filename strings as options for each GIF """
        name = http_address.split('/')[-1]
        name_root = name[:-4]
        path_frames = os.path.join(FRAME_PATH, name_root)
        gif_saved = '{path}/{name}_original.gif'.format(
            path=path_frames,
            date=self.start_time.strftime('%Y_%m_%d_%H-%M-%S'),
            name=name)
        new_gif = os.path.join(path_frames, name)
        assure_path_exists(path_frames)
        return dict(
            name=name,
            name_root=name_root,
            path_frames=path_frames,
            gif_saved=gif_saved,
            new_gif=new_gif
        )

    def terminate(self):
        self.running = False


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
    longer_weather.start()
    try:
        while longer_weather.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error('Keyboard exit')
        longer_weather.terminate()
        sys.exit(1)
