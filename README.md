# shallow-appify

## Introduction

Converts any executable to a non-self-contained mac app bundle which depends on system libraries. Other converters often
have problems when complex dependencies (e.g. PyQt) must be included. shallow-appify avoids these problems by
referencing present system libraries.

## Usage

    usage: shallow-appify [-h] [-d EXECUTABLE_ROOT_PATH]
                          [-e ENVIRONMENT_VARS [ENVIRONMENT_VARS ...]] [-i ICON_PATH]
                          [-g GROUP] [-n] [-o APP_PATH] [-v VERSION_STRING]
                          [--conda CONDA_REQ_FILE]
                          [--conda-channels CONDA_CHANNELS [CONDA_CHANNELS ...]]
                          [--extension-makefile EXTENSION_MAKEFILE]
                          executable_path

    Creates a runnable application for Mac OS X with references to system
    libraries. The result is a NON-self-contained app bundle.

    positional arguments:
      executable_path       Sets the executable that is started when the app is
                            opened.

    optional arguments:
      -h, --help            show this help message and exit
      -d EXECUTABLE_ROOT_PATH, --executable-directory EXECUTABLE_ROOT_PATH
                            Defines the executable root directory that will be
                            included in the app.
      -e ENVIRONMENT_VARS [ENVIRONMENT_VARS ...], --environment ENVIRONMENT_VARS [ENVIRONMENT_VARS ...]
                            Specifies which environment variables -- set on the
                            current interpreter startup -- shall be included in
                            the app bundle.
      -i ICON_PATH, --icon ICON_PATH
                            Image file that is used for app icon creation. It must
                            be quadratic with a resolution of 1024x1024 pixels or
                            more.
      -g GROUP, --group GROUP
                            Developer group name that is saved to the internal app
                            plist.
      -n, --hidden          Hides the app icon in the dock when given.
      -o APP_PATH, --output APP_PATH
                            Sets the path the app will be saved to.
      -v VERSION_STRING, --version VERSION_STRING
                            Specifies the version string of the program.
      --conda CONDA_REQ_FILE
                            (Python only) Creates a miniconda environment from the
                            given conda requirements file and includes it in the
                            app bundle. Can be used to create self-contained
                            python apps.
      --conda-channels CONDA_CHANNELS [CONDA_CHANNELS ...]
                            (Python only) A list of custom conda channels to
                            install packages that are not included in the main
                            anaconda distribution.
      --extension-makefile EXTENSION_MAKEFILE
                            (Python only) Path to a makefile for building python
                            extension modules. The makefile is called with the
                            target "app_extension_modules" and a variable
                            "PYLIBPATH" that holds the path to the conda python
                            library.
