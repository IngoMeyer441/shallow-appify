shallow-appify
==============

Converts any executable to a non-self-contained mac app bundle which depends on system libraries. Other converters often have problems when complex dependencies (e.g. PyQt) must be included. shallow-appify avoids these problems by referencing present system libraries.


Usage
=====

    usage: shallow-appify.py [-h] [-d EXECUTABLE_ROOT_PATH] [-i ICON_PATH]
                             [-e ENVIRONMENT_VARS [ENVIRONMENT_VARS ...]]
                             [-o APP_PATH] [-v VERSION_STRING]
                             executable_path

    positional arguments:
      executable_path       Sets the executable that is started when the app is
                            opened.

    optional arguments:
      -h, --help            show this help message and exit
      -d EXECUTABLE_ROOT_PATH, --executable-directory EXECUTABLE_ROOT_PATH
                            Defines the executable root directory that will be
                            included in the app.
      -i ICON_PATH, --icon ICON_PATH
                            Image file that is used for app icon creation. It must
                            be quadratic with a resolution of 1024x1024 pixels or
                            more.
      -e ENVIRONMENT_VARS [ENVIRONMENT_VARS ...], --environment ENVIRONMENT_VARS [ENVIRONMENT_VARS ...]
                            Specifies which environment variables -- set on the
                            current interpreter startup -- shall be included in
                            the app bundle.
      -o APP_PATH, --output APP_PATH
                            Sets the path the app will be saved to.
      -v VERSION_STRING, --version VERSION_STRING
                            Specifies the version string of the program.

