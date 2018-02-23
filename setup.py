# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import os
import subprocess
from setuptools import setup, find_packages
from shallow_appify._version import __version__


def get_long_description_from_readme(readme_filename='README.md'):
    rst_filename = '{}.rst'.format(os.path.splitext(os.path.basename(readme_filename))[0])
    created_tmp_rst = False
    if not os.path.isfile(rst_filename):
        try:
            subprocess.check_call(['pandoc', readme_filename, '-t', 'rst', '-o', rst_filename])
            created_tmp_rst = True
        except (OSError, subprocess.CalledProcessError):
            pass
    long_description = None
    if os.path.isfile(rst_filename):
        with codecs.open(rst_filename, 'r', 'utf-8') as readme_file:
            long_description = readme_file.read()
    if created_tmp_rst:
        os.remove(rst_filename)
    return long_description


long_description = get_long_description_from_readme()

setup(
    name='shallow-appify',
    version=__version__,
    packages=find_packages(),
    package_data={
        str('shallow_appify'): ['dmg_background.png']  # setuptools needs byte strings as keys when running Python 2.x
    },
    install_requires=[
        'Jinja2',
        'Pillow'
    ],
    entry_points={
        'console_scripts': [
            'shallow-appify = shallow_appify.shallow_appify:main',
        ]
    },
    author='Ingo Heimbach',
    author_email='i.heimbach@fz-juelich.de',
    description='Converts any executable to a non-self-contained mac app bundle which depends on system libraries.',
    long_description=long_description,
    license='MIT',
    url='https://github.com/IngoHeimbach/shallow-appify',
    keywords=['macOS', 'app', 'py2app'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities'
    ]
)
