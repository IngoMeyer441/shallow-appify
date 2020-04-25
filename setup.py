# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import os
import runpy
from setuptools import setup, find_packages


def get_version_from_pyfile(version_file="shallow_appify/_version.py"):
    file_globals = runpy.run_path(version_file)
    return file_globals["__version__"]


def get_long_description_from_readme(readme_filename="README.md"):
    long_description = None
    if os.path.isfile(readme_filename):
        with codecs.open(readme_filename, "r", "utf-8") as readme_file:
            long_description = readme_file.read()
    return long_description


version = get_version_from_pyfile()
long_description = get_long_description_from_readme()

setup(
    name="shallow-appify",
    version=version,
    packages=find_packages(),
    package_data={
        str("shallow_appify"): ["dmg_background.png"]  # setuptools needs byte strings as keys when running Python 2.x
    },
    install_requires=["Jinja2", "Pillow"],
    entry_points={"console_scripts": ["shallow-appify = shallow_appify.shallow_appify:main",]},
    author="Ingo Heimbach",
    author_email="i.heimbach@fz-juelich.de",
    description="Converts any executable to a non-self-contained mac app bundle which depends on system libraries.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/IngoHeimbach/shallow-appify",
    keywords=["macOS", "app", "py2app"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
)
