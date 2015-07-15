#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

__author__ = 'Ingo Heimbach'
__email__ = 'i.heimbach@fz-juelich.de'

__version_info__ = (0, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import argparse
import os
import os.path
import re
import shutil
import subprocess
import tempfile
from jinja2 import Template
from PIL import Image
import logging
logging.basicConfig(level=logging.WARNING)


INFO_PLIST_TEMPLATE = '''
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        {% if environ %}
            <key>LSEnvironment</key>
            <dict>
                {% for key, value in environ.iteritems() %}
                    <key>{{ key }}</key>
                    <string>{{ value }}</string>
                {% endfor %}
            </dict>
        {% endif %}
        <key>CFBundleDevelopmentRegion</key>
        <string>English</value>
        <key>CFBundleExecutable</key>
        <string>{{ executable }}</string>
        <key>CFBundleIconFile</key>
        <string>{{ icon_file }}</string>
        <key>CFBundleIdentifier</key>
        <string>de.fz-juelich.{{ name }}</string>
        <key>CFBundleInfoDictionaryVersion</key>
        <string>6.0</string>
        <key>CFBundleName</key>
        <string>{{ name }}</string>
        <key>CFBundleShortVersionString</key>
        <string>{{ short_version }}</string>
        <key>CFBundleVersion</key>
        <string>{{ version }}</string>
    </dict>
    </plist>
'''


class TemporaryDirectory(object):
    def __init__(self):
        self.tmp_dir = tempfile.mkdtemp()

    def __enter__(self):
        return self.tmp_dir

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)
        self.tmp_dir = None


def parse_args():
    parser = argparse.ArgumentParser(description='''
    Creates a runnable application for Mac OS X with references to
    system libraries. Therefore, the built app will NOT be self-contained.''')
    parser.add_argument('-d', '--source-directory', dest='source_directory_path', action='store', type=os.path.abspath,
                        help='Defines the source root directory that will be included in the app.')
    parser.add_argument('-i', '--icon', dest='icon', action='store', type=os.path.abspath,
                        help='Image file that is used for app icon creation. It must be quadratic with a resolution of 1024x1024 pixels or more.')
    parser.add_argument('-e', '--environment', dest='environ', action='store', nargs='+',
                        help='Specifies which environment varibles -- set on the current interpreter startup -- shall be included in the app bundle.')
    parser.add_argument('-o', '--output', dest='output', action='store', type=os.path.abspath,
                        help='Sets the path the app will be saved to.')
    parser.add_argument('-v', '--version', dest='version', action='store',
                        help='Specifies the version string of the program.')
    parser.add_argument('excutable_path', action='store', type=os.path.abspath, required=True,
                        help='Sets the executable that is started when the app is opened.')
    args = parser.parse_args()

    return args

def create_info_plist_content(app_name, version, executable_path, source_root_path=None, icon_path=None, environment_variable_list=None):
    def get_short_version(version):
        match_obj = re.search('\d+\.\d+(\.\d+)?', version)
        if match_obj is not None:
            short_version = match_obj.group()
            if not re.match('\d+\.\d+\.\d+', short_version):
                short_version += '.0'
        else:
            short_version = '0.0.0'
        return short_version

    vars = {'executable': os.path.relpath(executable_path, source_root_path),
            'icon_file': os.path.basename(icon_path),
            'name': app_name,
            'short_version': get_short_version(version),
            'version': version}

    if environment_variable_list is not None:
        environment_variables = dict(((key, os.environ[key]) for key in environment_variable_list))
        vars.update(environment_variables)

    template = Template(INFO_PLIST_TEMPLATE)
    info_plist = template.render(**vars)

    return info_plist

def create_icon_set(icon_path, iconset_out_path):
    with TemporaryDirectory as tmp_dir:
        tmp_icns_dir = '{tmp_dir}/icon.icns'.format(tmp_dir=tmp_dir)
        original_icon = Image.open(icon_path)
        for name, size in (('icon_{size}x{size}{suffix}.png'.format(size, suffix), factor*size)
                                for size in (16, 32, 128, 256, 512)
                                    for factor, suffix in ((1, ''), (2, '@2x'))):
            resized_icon = original_icon.resize((size, size), Image.ANTIALIAS)
            resized_icon.save('{icns_dir}/{icon_name}'.format(icns_dir=tmp_icns_dir, icon_name=name))
        subprocess.call(('iconutil', '--convert', 'icns', tmp_icns_dir, '--output', iconset_out_path))

def create_app(app_path, version, executable_path, source_root_path=None, icon_path=None, environment_variable_list=None):
    pass

def main():
    pass


if __name__ == '__main__':
    main()
