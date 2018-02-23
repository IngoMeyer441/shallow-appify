# coding: utf-8

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import codecs
import fnmatch
import itertools
import os
import re
import shutil
import subprocess
from jinja2 import Template
from .util import command
from .util.binary_replace import binary_replace

__author__ = 'Ingo Heimbach'
__email__ = 'i.heimbach@fz-juelich.de'

PY_PRE_STARTUP_CONDA_SETUP = '''
#!/bin/bash
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${SCRIPT_DIR}

function fix_prefix {
    local SAVED_PREFIX
    local REAL_PREFIX

    SAVED_PREFIX=$(sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' <../Resources/application_path_prefix)
    REAL_PREFIX=$(cd ../.. && pwd | tr -d '\\n')

    if [ "${SAVED_PREFIX}" != "${REAL_PREFIX}" ]; then
        if [ -w "../Resources/application_path_prefix" ]; then
            >&2 echo "INFO: Replacing application prefix ${SAVED_PREFIX} with ${REAL_PREFIX} ..."
            while read -r MATCHING_FILE ; do
                if file --mime "${MATCHING_FILE}" | grep -q "charset=binary"; then
                    ../Resources/binary_replace.py "${MATCHING_FILE}" "${SAVED_PREFIX}" "${REAL_PREFIX}"
                else
                    sed -i '' "s!${SAVED_PREFIX}!${REAL_PREFIX}!g" "${MATCHING_FILE}"
                fi
            done < <(grep -rl --exclude='*.pyc' "${SAVED_PREFIX}" ../Resources/conda_env)
            echo "${REAL_PREFIX}">../Resources/application_path_prefix
        else
            >&2 echo "WARNING: The app has no write permissions to change location prefixes!"
        fi
    fi
}

fix_prefix
source ../Resources/conda_env/bin/activate ../Resources/conda_env
python __startup__.py
'''.strip()

PY_STARTUP_SCRIPT = '''
{{ shebang }}
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
        if child.tag == 'key' and (child.text.startswith('CF') or   # CoreFoundation key
                                   child.text in ['LSUIElement', 'NSSupportsAutomaticGraphicsSwitching']):
            current_key = child.text
        elif current_key is not None:
            if child.text is not None:
                bundle_info[current_key] = child.text
            else:
                bundle_info[current_key] = (child.tag == 'true')
            current_key = None

def main():
    fix_current_working_directory()
    set_cf_keys()
    import {{ main_module }}
    {{ main_module }}.main()    # a main function is required
if __name__ == '__main__':
    main()
'''.strip()

_plugin_name_ = 'Python'
_file_ext_ = 'py'

_PY_STARTUP_SCRIPT_NAME = '__startup__.py'
_ENV_STARTUP_SCRIPT_NAME = '__startup__.sh'
_CONDA_DEFAULT_PACKAGES = ('pyobjc-framework-cocoa', )
_CONDA_DEFAULT_CHANNELS = ('https://conda.binstar.org/erik', )
_EXT_PYLIB_VARIABLE = 'PYLIBPATH'
_EXT_MAKEFILE_TARGET = 'app_extension_modules'

_create_conda_env = False
_requirements_file = None
_conda_channels = None
_extension_makefile = None
_conda_gr_included = False


class CondaError(Exception):
    pass


class LibPatchingError(Exception):
    pass


class PrecompileError(Exception):
    pass


class ExtensionModuleError(Exception):
    pass


def get_command_line_arguments():
    arguments = [
        (
            ('--conda', ), {
                'dest':
                'conda_req_file',
                'action':
                'store',
                'type':
                os.path.abspath,
                'help':
                'Creates a miniconda environment from the given conda requirements file '
                'and includes it in the app bundle. Can be used to create self-contained '
                'python apps.'
            }
        ), (
            ('--conda-channels', ), {
                'dest':
                'conda_channels',
                'action':
                'store',
                'nargs':
                '+',
                'help':
                'A list of custom conda channels to install packages that are not '
                'included in the main anaconda distribution.'
            }
        ), (
            ('--extension-makefile', ), {
                'dest':
                'extension_makefile',
                'action':
                'store',
                'type':
                os.path.abspath,
                'help':
                'Path to a makefile for building python extension modules. The '
                'makefile is called with the target "{target}" and a variable '
                '"{libvariable}" that holds the path to the conda python '
                'library.'.format(target=_EXT_MAKEFILE_TARGET, libvariable=_EXT_PYLIB_VARIABLE)
            }
        )
    ]
    return arguments


def parse_command_line_arguments(args):
    global _create_conda_env, _requirements_file, _conda_channels, _extension_makefile, _conda_gr_included

    def is_gr_in_conda_requirements(requirements_file):
        with codecs.open(requirements_file, 'r', 'utf-8') as f:
            found_gr = any((line.startswith('gr=') for line in f))
        return found_gr

    checked_args = {}
    if args.conda_req_file is not None:
        checked_args['python_conda'] = args.conda_req_file
        _requirements_file = args.conda_req_file
        _create_conda_env = True
        if args.conda_channels is not None:
            _conda_channels = args.conda_channels
        if args.extension_makefile is not None:
            _extension_makefile = args.extension_makefile
        _conda_gr_included = is_gr_in_conda_requirements(_requirements_file)
    return checked_args


def pre_create_app(**kwargs):
    pass


def setup_startup(app_path, executable_path, app_executable_path, executable_root_path, macos_path, resources_path):
    def create_python_startup_script(main_module, shebang):
        template = Template(PY_STARTUP_SCRIPT)
        startup_script = template.render(main_module=main_module, shebang=shebang)
        return startup_script

    def patch_lib_python(env_path):
        env_path = os.path.abspath(env_path)
        python_dir_path = os.path.join(env_path, 'bin')
        lib_pattern = 'libpython*.dylib'
        lib_dir_path = os.path.join(env_path, 'lib')
        python_lib_pathes = tuple(
            [
                os.path.join(lib_dir_path, path)
                for path in os.listdir(lib_dir_path) if fnmatch.fnmatch(path, lib_pattern)
            ]
        )
        for python_lib_path in python_lib_pathes:
            rel_python_lib_path = os.path.join('@executable_path', os.path.relpath(python_lib_path, python_dir_path))
            with codecs.open(os.devnull, 'w', 'utf-8') as dummy:
                try:
                    subprocess.check_call(
                        ['install_name_tool', '-id', rel_python_lib_path, python_lib_path], stdout=dummy, stderr=dummy
                    )
                except subprocess.CalledProcessError:
                    raise LibPatchingError('Could not patch the anaconda python library.')

    def create_conda_env():
        def create_env():
            conda_channels = _conda_channels or []
            with codecs.open(os.devnull, 'w', 'utf-8') as dummy:
                env_path = os.path.join(resources_path, 'conda_env')
                try:
                    subprocess.check_call(
                        ['conda', 'create', '-p', env_path, '--file', _requirements_file, '--copy', '--quiet', '--yes']
                        + list(itertools.chain(*[('-c', channel) for channel in conda_channels])),
                        stdout=dummy,
                        stderr=dummy
                    )
                    subprocess.check_call(
                        ' '.join(
                            [
                                'source',
                                os.path.join(env_path, 'bin/activate'), env_path, ';', 'conda', 'install', '--copy',
                                '--quiet', '--yes'
                            ] + list(_CONDA_DEFAULT_PACKAGES) +
                            list(itertools.chain(*[('-c', channel) for channel in _CONDA_DEFAULT_CHANNELS]))
                        ),
                        stdout=dummy,
                        stderr=dummy,
                        shell=True
                    )
                except subprocess.CalledProcessError:
                    raise CondaError('The conda environment could not be installed.')
            return env_path

        env_path = create_env()
        patch_lib_python(env_path)
        return env_path

    def make_conda_portable(env_path):
        CONDA_BIN_PATH = 'bin/conda'
        CONDA_ACTIVATE_PATH = 'bin/activate'
        CONDA_MISSING_PACKAGES = ('conda', 'enum', 'ruamel_yaml', 'requests')

        def fix_links_to_system_files():
            for root_path, dirnames, filenames in os.walk(env_path):
                dirpaths = [os.path.join(root_path, dirname) for dirname in dirnames]
                filepaths = [os.path.join(root_path, filename) for filename in filenames]
                link_dirpaths = [
                    dirpath for dirpath in dirpaths
                    if os.path.islink(dirpath) and not os.path.realpath(dirpath).startswith(env_path)
                ]
                link_filepaths = [
                    filepath for filepath in filepaths
                    if os.path.islink(filepath) and not os.path.realpath(filepath).startswith(env_path)
                ]
                for link_dirpath in link_dirpaths:
                    real_dirpath = os.path.realpath(link_dirpath)
                    os.remove(link_dirpath)
                    shutil.copytree(real_dirpath, os.path.join(root_path, os.path.basename(link_dirpath)))
                for link_filepath in link_filepaths:
                    real_filepath = os.path.realpath(link_filepath)
                    os.remove(link_filepath)
                    shutil.copy(real_filepath, os.path.join(root_path, os.path.basename(link_filepath)))

        def fix_activate_script():
            DELETE_LINE_PART = 'checkenv'
            DELETE_LINE_COUNT = 5
            REPLACE_LINE_PART = '_NEW_PART='
            REPLACE_LINE_INSERT = '_NEW_PART=$_CONDA_DIR'
            full_conda_activate_path = os.path.join(env_path, CONDA_ACTIVATE_PATH)
            found_line_to_delete = False
            found_line_to_replace = False
            skip_line_num = 0
            new_lines = []
            with codecs.open(full_conda_activate_path, 'r', 'utf-8') as f:
                for line in f:
                    if skip_line_num > 0:
                        skip_line_num -= 1
                        continue
                    if not found_line_to_delete:
                        if DELETE_LINE_PART in line:
                            found_line_to_delete = True
                            skip_line_num = DELETE_LINE_COUNT - 1
                            continue
                    if not found_line_to_replace:
                        if REPLACE_LINE_PART in line:
                            found_line_to_replace = True
                            new_lines.append('{}\n'.format(REPLACE_LINE_INSERT))
                            continue
                    new_lines.append(line)
            with codecs.open(full_conda_activate_path, 'w', 'utf-8') as f:
                f.writelines(new_lines)

        def fix_conda_shebang():
            full_conda_bin_path = os.path.join(env_path, CONDA_BIN_PATH)
            with codecs.open(full_conda_bin_path, 'r', 'utf-8') as f:
                lines = f.readlines()
            # replace shebang line
            lines[0] = '#!/usr/bin/env python\n'
            with codecs.open(full_conda_bin_path, 'w', 'utf-8') as f:
                f.writelines(lines)

        def copy_missing_conda_packages():
            ANACONDA_PYTHON_PACKAGES_PATH = 'lib/python2.7/site-packages'
            CONDAENV_PYTHON_PACKAGES_PATH = 'lib/python2.7/site-packages'

            def get_system_anaconda_root_path():
                anaconda_dir_path = None
                system_conda_bin_path = command.which('conda')
                if system_conda_bin_path:
                    with codecs.open(system_conda_bin_path, 'r', 'utf-8') as f:
                        shebang_line = f.readline()
                    match_obj = re.match('#!(.*)/bin/python', shebang_line)
                    if match_obj:
                        anaconda_dir_path = match_obj.group(1)
                return anaconda_dir_path

            system_anaconda_root_path = get_system_anaconda_root_path()
            full_anaconda_python_packages_path = os.path.join(system_anaconda_root_path, ANACONDA_PYTHON_PACKAGES_PATH)
            full_condaenv_python_packages_path = os.path.join(env_path, CONDAENV_PYTHON_PACKAGES_PATH)
            for package in CONDA_MISSING_PACKAGES:
                shutil.copytree(
                    os.path.join(full_anaconda_python_packages_path, package),
                    os.path.join(full_condaenv_python_packages_path, package)
                )

        def fix_application_path_prefix():
            app_name = os.path.splitext(os.path.basename(app_path))[0]
            target_application_path_prefix = '/Applications/{app_name}.app'.format(app_name=app_name)
            current_application_path_prefix = os.path.abspath(os.path.join(env_path, '../../..'))
            matching_files = subprocess.check_output(
                ['grep', '-rl', "--exclude='*.pyc'", current_application_path_prefix, env_path]
            ).strip().split('\n')
            text_files = []
            binary_files = []
            for matching_file in matching_files:
                if 'charset=binary' in subprocess.check_output(['file', '--mime', matching_file]):
                    binary_files.append(matching_file)
                else:
                    text_files.append(matching_file)
            for text_file in text_files:
                sed_pattern = 's!{current_prefix}!{target_prefix}!g'.format(
                    current_prefix=current_application_path_prefix, target_prefix=target_application_path_prefix
                )
                subprocess.check_call(['sed', '-i', '', sed_pattern, text_file])
            for binary_file in binary_files:
                binary_replace(binary_file, current_application_path_prefix, target_application_path_prefix)
            with codecs.open(os.path.join(env_path, '../application_path_prefix'), 'w', 'utf-8') as f:
                f.write(target_application_path_prefix)

        fix_links_to_system_files()
        fix_activate_script()
        fix_conda_shebang()
        copy_missing_conda_packages()
        fix_application_path_prefix()

    def fix_conda_gr(env_path):
        def create_missing_library_links():
            library_directory = os.path.join(env_path, 'lib')
            site_package_directory = os.path.join(env_path, 'lib/python2.7/site-packages')
            for rel_lib_path in ('gr/libGR.so', 'gr3/libGR3.so'):
                os.symlink(
                    os.path.relpath(
                        os.path.join(site_package_directory, rel_lib_path),
                        library_directory
                    ), os.path.join(library_directory, os.path.basename(rel_lib_path))
                )

        create_missing_library_links()

    def precompile_python_files():
        with codecs.open(os.devnull, 'w', 'utf-8') as dummy:
            try:
                subprocess.check_call(['python', '-m', 'compileall', macos_path], stdout=dummy, stderr=dummy)
            except subprocess.CalledProcessError:
                raise PrecompileError('Python modules could not be precompiled.')

    def build_extension_modules(env_path):
        def get_makefile_path():
            if executable_root_path is not None and \
               _extension_makefile.startswith(os.path.abspath(executable_root_path)):
                makefile_path = os.path.join(macos_path, os.path.relpath(_extension_makefile, executable_root_path))
            else:
                makefile_path = _extension_makefile
            return makefile_path

        env_path = os.path.abspath(env_path)
        lib_dir_path = os.path.join(env_path, 'lib')
        makefile_path = get_makefile_path()
        makefile_dir_path = os.path.dirname(makefile_path)
        with codecs.open(os.devnull, 'w', 'utf-8') as dummy:
            try:
                subprocess.check_call(
                    [
                        'make', '-C', makefile_dir_path, _EXT_MAKEFILE_TARGET,
                        '{var}={lib_dir_path}'.format(var=_EXT_PYLIB_VARIABLE, lib_dir_path=lib_dir_path)
                    ],
                    stdout=dummy,
                    stderr=dummy
                )
            except subprocess.CalledProcessError:
                raise ExtensionModuleError('Extension modules could not be built.')

    main_module = os.path.splitext(app_executable_path)[0].replace('/', '.')
    with codecs.open(executable_path, 'r', 'utf-8') as f:
        shebang = f.readline().strip()
    if not shebang.startswith('#!'):
        shebang = '#!/usr/bin/env python'
    python_startup_script = create_python_startup_script(main_module, shebang)
    with codecs.open(os.path.join(macos_path, _PY_STARTUP_SCRIPT_NAME), 'w', 'utf-8') as f:
        f.write(python_startup_script)
    if _create_conda_env:
        env_path = create_conda_env()
        make_conda_portable(env_path)
        if _conda_gr_included:
            fix_conda_gr(env_path)
        precompile_python_files()
        if _extension_makefile is not None:
            build_extension_modules(env_path)
        env_startup_script = PY_PRE_STARTUP_CONDA_SETUP
        with codecs.open(os.path.join(macos_path, _ENV_STARTUP_SCRIPT_NAME), 'w',
                         'utf-8') as f:
            f.write(env_startup_script)
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'util/binary_replace.py'),
            os.path.join(resources_path, 'binary_replace.py')
        )
        new_executable_path = _ENV_STARTUP_SCRIPT_NAME
    else:
        new_executable_path = _PY_STARTUP_SCRIPT_NAME

    return new_executable_path


def post_create_app(**kwargs):
    pass
