# shallow-appify
Converts any executable to a non-self-contained mac app bundle which depends on system libraries. Other converters often have problems when large dependencies (e.g. PyQt) must be included. shallow-appify avoids these problems by referencing present system libraries.
