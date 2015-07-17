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
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    {% if environment -%}
    <key>LSEnvironment</key>
    <dict>
        {% for key, value in environment.iteritems() -%}
        <key>{{ key }}</key>
        <string>{{ value }}</string>
        {% endfor -%}
    </dict>
    {% endif -%}
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleExecutable</key>
    <string>{{ executable }}</string>
    {% if icon_file -%}
    <key>CFBundleIconFile</key>
    <string>{{ icon_file }}</string>
    {% endif -%}
    <key>CFBundleIdentifier</key>
    <string>de.fz-juelich.{{ name }}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{{ name }}</string>
    <key>CFBundleDisplayName</key>
    <string>{{ name }}</string>
    <key>CFBundleShortVersionString</key>
    <string>{{ short_version }}</string>
    <key>CFBundleVersion</key>
    <string>{{ version }}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
</dict>
</plist>
'''.strip()

PKG_INFO_CONTENT = 'APPL????'

STARTUP_SKRIPT = '''
#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals

import os
import os.path
from xml.etree import ElementTree as ET
from Foundation import NSBundle

def fix_current_working_directory():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def set_cf_keys():
    bundle = NSBundle.mainBundle()
    bundle_info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    info_plist = ET.parse('../Info.plist')
    root = info_plist.getroot()
    plist_dict = root.find('dict')
    current_key = None
    for child in plist_dict:
        if child.tag == 'key' and child.text.startswith('CF'):  # CoreFoundation key
            current_key = child.text
        elif current_key is not None:
            bundle_info[current_key] = child.text
            current_key = None

def main():
    fix_current_working_directory()
    set_cf_keys()
    import {{ main_module }}
    {{ main_module }}.main()    # a main function is required
if __name__ == '__main__':
    main()
'''.strip()




class TemporaryDirectory(object):
    def __init__(self):
        self.tmp_dir = tempfile.mkdtemp()

    def __enter__(self):
        return self.tmp_dir

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)
        self.tmp_dir = None


class Arguments(object):
    def __init__(self, **kwargs):
        super(Arguments, self).__setattr__('_members', {})
        for key, value in kwargs.iteritems():
            self._members[key] = value

    def __getattr__(self, attr):
        return self._members[attr]

    def __setattr__(self, key, value):
        raise NotImplementedError

    def __getitem__(self, item):
        return getattr(self, item)

    def keys(self):
        return self._members.keys()


def parse_args():
    def parse_commandline():
        parser = argparse.ArgumentParser(description='''
        Creates a runnable application for Mac OS X with references to
        system libraries. Therefore, the built app will NOT be self-contained.''')
        parser.add_argument('-d', '--source-directory', dest='source_root_path', action='store', type=os.path.abspath,
                            help='Defines the source root directory that will be included in the app.')
        parser.add_argument('-i', '--icon', dest='icon_path', action='store', type=os.path.abspath,
                            help='Image file that is used for app icon creation. It must be quadratic with a resolution of 1024x1024 pixels or more.')
        parser.add_argument('-e', '--environment', dest='environment_keys', action='store', nargs='+',
                            help='Specifies which environment varibles -- set on the current interpreter startup -- shall be included in the app bundle.')
        parser.add_argument('-o', '--output', dest='app_path', action='store', type=os.path.abspath,
                            help='Sets the path the app will be saved to.')
        parser.add_argument('-v', '--version', dest='version_string', action='store',
                            help='Specifies the version string of the program.')
        parser.add_argument('executable_path', action='store', type=os.path.abspath,
                            help='Sets the executable that is started when the app is opened.')
        args = parser.parse_args()
        return args

    args = parse_commandline()
    source_root_path = args.source_root_path
    icon_path = args.icon_path
    environment_keys = args.environment_keys
    if args.app_path is not None:
        app_path = args.app_path
    else:
        app_path = '{path_without_ext}.app'.format(path_without_ext=os.path.splitext(os.path.abspath(args.executable_path))[0])
    if args.version_string is not None:
        version_string = args.version_string
    else:
        version_string = '0.0.0'
    executable_path = os.path.abspath(args.executable_path)

    return Arguments(source_root_path=source_root_path,
                     icon_path=icon_path,
                     environment_keys=environment_keys,
                     app_path=app_path,
                     version_string=version_string,
                     executable_path=executable_path)

def create_info_plist_content(app_name, version, executable_path, source_root_path=None, icon_path=None, environment_keys=None):
    def get_short_version(version):
        match_obj = re.search('\d+\.\d+(\.\d+)?', version)
        if match_obj is not None:
            short_version = match_obj.group()
            if not re.match('\d+\.\d+\.\d+', short_version):
                short_version += '.0'
        else:
            short_version = '0.0.0'
        return short_version

    if source_root_path is None:
        source_root_path = os.path.dirname(executable_path)

    vars = {'executable': os.path.relpath(executable_path, source_root_path),
            'icon_file': os.path.basename(icon_path) if icon_path is not None else None,
            'name': app_name,
            'short_version': get_short_version(version),
            'version': version}

    if environment_keys is not None:
        environment_variables = dict(((key, os.environ[key]) for key in environment_keys))
        vars['environment'] = environment_variables

    template = Template(INFO_PLIST_TEMPLATE)
    info_plist = template.render(**vars)

    return info_plist

def create_python_startup_script(main_module_name):
    template = Template(STARTUP_SKRIPT)
    startup_script = template.render(main_module=main_module_name)

    return startup_script

def create_icon_set(icon_path, iconset_out_path):
    with TemporaryDirectory() as tmp_dir:
        tmp_icns_dir = '{tmp_dir}/icon.iconset'.format(tmp_dir=tmp_dir)
        os.mkdir(tmp_icns_dir)
        original_icon = Image.open(icon_path)
        for name, size in (('icon_{size}x{size}{suffix}.png'.format(size=size, suffix=suffix), factor*size)
                                for size in (16, 32, 128, 256, 512)
                                    for factor, suffix in ((1, ''), (2, '@2x'))):
            resized_icon = original_icon.resize((size, size), Image.ANTIALIAS)
            resized_icon.save('{icns_dir}/{icon_name}'.format(icns_dir=tmp_icns_dir, icon_name=name))
        subprocess.call(('iconutil', '--convert', 'icns', tmp_icns_dir, '--output', iconset_out_path))

def create_app(app_path, version_string, executable_path, source_root_path=None, icon_path=None, environment_keys=None):
    def abs_path(relative_bundle_path, base=None):
        return '{app_path}/{dir}'.format(app_path=app_path if base is None else base, dir=relative_bundle_path)

    def setup_python_startup():
        main_module = os.path.splitext(app_executable_path)[0].replace('/', '.')
        python_startup_script = create_python_startup_script(main_module)
        new_executable_path = abs_path('___startup___.py', macos_path)
        with open(new_executable_path, 'w') as f:
            f.writelines(python_startup_script.encode('utf-8'))
        return new_executable_path

    def write_info_plist():
        info_plist_content = create_info_plist_content(app_name, version_string, app_executable_path, source_root_path,
                                                       bundle_icon_path, environment_keys)
        with open(abs_path('Info.plist', contents_path) , 'w') as f:
            f.writelines(info_plist_content.encode('utf-8'))

    def write_pkg_info():
        with open(abs_path('PkgInfo', contents_path) , 'w') as f:
            f.write(PKG_INFO_CONTENT)

    def copy_source():
        if source_root_path is None:
            shutil.copy(executable_path, macos_path)
        else:
            os.rmdir(macos_path)
            shutil.copytree(source_root_path, macos_path)

    def set_file_permissions():
        os.chmod(app_executable_path, 0555)

    directory_structure = ('Contents', 'Contents/MacOS', 'Contents/Resources')
    contents_path, macos_path, resources_path = (abs_path(dir) for dir in directory_structure)
    bundle_icon_path = abs_path('Icon.icns', resources_path) if icon_path is not None else None
    app_name = os.path.splitext(os.path.basename(app_path))[0]
    if source_root_path is not None:
        app_executable_path = os.path.relpath(executable_path, source_root_path)
    else:
        app_executable_path = os.path.basename(executable_path)

    for current_path in (abs_path(dir) for dir in directory_structure):
        os.makedirs(current_path)
    copy_source()
    if icon_path is not None:
        create_icon_set(icon_path, bundle_icon_path)
    if app_executable_path.endswith('.py'):
        app_executable_path = setup_python_startup()
    write_info_plist()
    write_pkg_info()
    set_file_permissions()

def main():
    args = parse_args()
    create_app(**args)


if __name__ == '__main__':
    main()
