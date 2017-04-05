#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
from flask import Flask
from flask import send_file

INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
COMB_PATH = os.path.join(INSTALL_DIRECTORY, 'combined')

logger = logging.basicConfig()

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=tmpl_dir)


@app.route('/', methods=('GET', 'POST'))
def default_page():
    list_files = []
    for dir_name, _, file_names in os.walk(COMB_PATH):
        for each_name in sorted(file_names):
            if each_name.endswith('.gif'):
                list_files.append(os.path.join(dir_name, each_name))
    return send_file(list_files[-1], mimetype='image/gif')


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
