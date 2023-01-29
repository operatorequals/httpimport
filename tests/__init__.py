import sys
import unittest

import httpimport

# Define Interpreter Type
PYTHON = "cpython"
if ".NETFramework".lower() in sys.version.lower():
    PYTHON = "ironpython"
elif "JDK".lower() in sys.version.lower() or "java" in sys.version.lower():
    PYTHON = "jython"
elif "pypy".lower() in sys.version.lower():
    PYTHON = "pypy"

# Define HTTP Servers
SERVER_HOST = '127.0.0.1'
HTTP_PORT = 8000
PROXY_PORT = 8080
BASIC_AUTH_PORT = 8001
BASIC_AUTH_PROXY_PORT = 8081
HTTPS_PORT = 8443
PROXY_TLS_PORT = 8480

BASIC_AUTH_CREDS = 'dXNlcm5hbWU6cGFzc3dvcmQ='  # username:password
ZIP_PASSWORD = 'P@ssw0rd!'
WEB_DIRECTORY = 'test_web_directory/'
PROXY_HEADER = ('x-proxy', 'httpimport-proxy')
HTTPS_CERT = 'tests/certs/server.pem'
PROXY_TLS_CERT = 'tests/certs/proxy.pem'

# Define filepath for test profiles
PROFILE_PATH = 'tests/profiles/'

# Modules used for testing
TEST_MODULES = [
    'test_module',
    'test_package',
    'test_package.a',
    'test_package.b',
    'test_package.c',
    'test_package.b.mod',
    'test_package.b.mod2',
    'dependent_package',

    'sample',  # PyPI project: https://pypi.org/project/sampleproject
    'distlib',  # PyPI project: https://pypi.org/project/distlib
]

# URLs that provide test data
URLS = {
    "web_dir": "http://localhost:%d/",
    "tar_bz": "http://localhost:%d/test_package.tar.bz2",
    "tar_corrupt": "http://localhost:%d/test_package.corrupted.tar",
    "tar_xz": "http://localhost:%d/test_package.tar.xz",
    "tar_gz": "http://localhost:%d/test_package.tar.gz",
    "tar": "http://localhost:%d/test_package.tar",
    "zip": "http://localhost:%d/test_package.zip",
    "zip_encrypt": "http://localhost:%d/test_package.enc.zip",
}


class HttpImportTest(unittest.TestCase):
    # Base class to expose setUp, tearDown methods

    def tearDown(self):
        # Remove all possibly loaded modules
        for module in TEST_MODULES:
            sys.modules.pop(module, None)

        # Get back to defaults
        httpimport.set_profile(httpimport._DEFAULT_INI_CONFIG)
