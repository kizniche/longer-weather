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
    try:
        for http_address in GIF_HTTP_FILES:
            unique_name = '{base}_{prefix}'.format(
                base=http_address['base_address'].split('/')[-1],
                prefix=http_address['file_prefix'])
            # webm = os.path.join(
            #     FRAME_PATH, '{file}.webm'.format(file=unique_name))
            # return send_file(webm, mimetype='video/webm')
            gif = os.path.join(
                FRAME_PATH, '{file}.gif'.format(file=unique_name))
            return send_file(gif, mimetype='image/gif')
    except Exception:
        return '', 204


@app.route('/<int:gif>')
def gif_page(gif):
    try:
        if int(gif) >= len(GIF_HTTP_FILES) or int(gif) < 0:
            return '', 204

        unique_name = '{base}_{prefix}'.format(
            base=GIF_HTTP_FILES[int(gif)]['base_address'].split('/')[-1],
            prefix=GIF_HTTP_FILES[int(gif)]['file_prefix'])
        gif = os.path.join(
            FRAME_PATH, '{file}.gif'.format(file=unique_name))
        return send_file(gif, mimetype='image/gif')
    except Exception:
        return '', 204


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
