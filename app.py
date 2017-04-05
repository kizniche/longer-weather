#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
from flask import Flask
from flask import send_file

from config import COMB_PATH
from config import GIF_HTTP_FILES

logger = logging.basicConfig()

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=tmpl_dir)


@app.route('/', methods=('GET', 'POST'))
def default_page():
    list_files = {}
    for each_gif in GIF_HTTP_FILES:
        list_files[each_gif] = []
        for dir_name, _, file_names in os.walk(COMB_PATH):
            for each_name in sorted(file_names):
                if each_name.endswith('.gif'):
                    list_files[each_gif].append(os.path.join(dir_name, each_name))

    file_name = list_files[GIF_HTTP_FILES[0]][-1]

    return send_file(file_name, mimetype='image/gif')


@app.route('/<period>', methods=('GET', 'POST'))
def id_stats(period):
    filename = 'error.gif'
    return send_file(filename, mimetype='image/gif')


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

    app.run(host='0.0.0.0', port=6000, debug=debug)
