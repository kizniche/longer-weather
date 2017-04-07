#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
from flask import Flask
from flask import send_file
from config import FRAME_PATH
from config import GIF_HTTP_FILES

logger = logging.basicConfig()

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=tmpl_dir)


@app.route('/')
def default_page():
    for http_address in GIF_HTTP_FILES:
        name = http_address['address'].split('/')[-1]
        name_root = name[:-4]
        path_frames = os.path.join(FRAME_PATH, name_root)
        new_gif = os.path.join(path_frames, name)
        return send_file(new_gif, mimetype='image/gif')


@app.route('/<int:gif>')
def gif_page(gif):
    if int(gif) >= len(GIF_HTTP_FILES) or int(gif) < 0:
        return ('', 204)

    name = GIF_HTTP_FILES[int(gif)]['address'].split('/')[-1]
    name_root = name[:-4]
    path_frames = os.path.join(FRAME_PATH, name_root)
    new_gif = os.path.join(path_frames, name)
    return send_file(new_gif, mimetype='image/gif')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Longer Weather GIF server',
        formatter_class=argparse.RawTextHelpFormatter)

    options = parser.add_argument_group('Options')
    options.add_argument('-d', '--debug', action='store_true',
                         help='Run Flask with debug=True (Default: False)')

    args = parser.parse_args()
    debug = args.debug

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)

    app.run(host='0.0.0.0', port=5000, debug=debug)
