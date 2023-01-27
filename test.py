import logging
import os
import sys
import unittest
from random import randint
from urllib.error import HTTPError
from urllib.request import urlopen

import httpimport
import test_servers

logging.getLogger('httpimport').setLevel(logging.DEBUG)

PYTHON = "cpython"
if ".NETFramework".lower() in sys.version.lower():
    PYTHON = "ironpython"
elif "JDK".lower() in sys.version.lower() or "java" in sys.version.lower():
    PYTHON = "jython"
elif "pypy".lower() in sys.version.lower():
    PYTHON = "pypy"

TEST_MODULES = [
    'test_module',
    'test_package',
    'test_package.a',
    'test_package.b',
    'test_package.b.mod',
    'test_package.b.mod2',
    'dependent_package',

]

PORT = 8000
PROXY_PORT = 8080
BASIC_AUTH_PORT = 8001

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

BASIC_CONFIG = """
[{url}]

allow-plaintext: True
"""

httpimport.INSECURE = True

class Test(unittest.TestCase):

    def tearDown(self):
        # Remove all possibly loaded modules
        for module in TEST_MODULES:
            sys.modules.pop(module, None)
        # Remove the HTTP Proxy EnvVar honoured by urllib[2]
        os.environ['HTTP_PROXY'] = ''
        # Get back to defaults
        httpimport.set_profile(httpimport._DEFAULT_INI_CONFIG)

    def test_headers(self):
        #use the http method and parse the headers key
        resp = httpimport.http(URLS['web_dir'] % PORT)
        self.assertTrue('python' in resp['headers']['server'].lower())

    def test_simple_HTTP(self):
        # base package import
        with httpimport.remote_repo(URLS['web_dir'] % PORT):
            import test_package
        self.assertTrue(test_package)

        # subpackage with local imports
        with httpimport.remote_repo(URLS['web_dir'] % PORT):
            import test_package.b
        self.assertTrue(test_package.b.mod.module_name()
                        == test_package.b.mod2.mod2val)

    def test_basic_auth_HTTP(self):

        url = URLS['web_dir'] % BASIC_AUTH_PORT
        httpimport.set_profile("""[{url}]
headers:
    Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
        """.format(url=url))
        with httpimport.remote_repo(url):
            import test_package
        self.assertTrue(test_package)

    def test_basic_auth_HTTP_fail(self):

        self.assertFalse('test_package' in sys.modules)
        url = URLS['web_dir'] % BASIC_AUTH_PORT
        httpimport.set_profile("""[{url}]
# Wrong Password
headers:
    Authorization: Basic dXNlcm5hbWU6d3JvbmdfcGFzc3dvcmQ=
        """.format(url=url))
        with httpimport.remote_repo(url):
            try:
                import test_package
            except (ImportError, KeyError) as e:
                self.assertTrue(e)

    def test_dependent_HTTP(self):

        with httpimport.remote_repo(URLS['web_dir'] % PORT):
            import dependent_package
        self.assertTrue(dependent_package)

    def test_simple_HTTP_fail(self):

        with httpimport.remote_repo(URLS['web_dir'] % PORT):
            try:
                import test_package_nonexistent
            except (ImportError, KeyError) as e:
                self.assertTrue(e)

    def test_tarbz2_import(self):
        self.assertFalse('test_package' in sys.modules)

        with httpimport.remote_repo(
            URLS['tar_bz'] % PORT,
        ):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    def test_autodetect_corrupt_file(self):
        self.assertFalse('test_package' in sys.modules)

        try:
            with httpimport.remote_repo(
                URLS['tar_corrupt'] % PORT,
            ):
                import test_package
        except (ImportError, KeyError) as e:
            self.assertTrue(e)

        self.assertFalse('test_package' in sys.modules)

    def test_tarxz_import(self):
        self.assertFalse('test_package' in sys.modules)
        # Pass the test in IronPython, which does not support tar.xz lzma
        if PYTHON == "ironpython":
            self.assertTrue(True)
            return

        with httpimport.remote_repo(
            URLS['tar_xz'] % PORT,
        ):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    def test_targz_import(self):
        self.assertFalse('test_package' in sys.modules)

        with httpimport.remote_repo(
            URLS['tar_gz'] % PORT,
        ):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    def test_tar_import(self):
        self.assertFalse('test_package' in sys.modules)

        with httpimport.remote_repo(
            URLS['tar'] % PORT,
        ):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    def test_zip_import(self):
        self.assertFalse('test_package' in sys.modules)
        url = URLS['zip'] % PORT
        httpimport.set_profile("""[{url}]
zip-password:
        """.format(url=url))
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    # Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
    def test_zip_import_w_pwd(self):
        self.assertFalse('test_package' in sys.modules)
        url = URLS['zip_encrypt'] % PORT
        httpimport.set_profile("""[{url}]
zip-password: P@ssw0rd!
        """.format(url=url))
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue('test_package' in sys.modules)

    # Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
    def test_zip_import_w_pwd_wrong(self):
        self.assertFalse('test_package' in sys.modules)
        url = URLS['zip_encrypt'] % PORT
        httpimport.set_profile("""[{url}]
# wrong password!
zip-password: XXXXXXXX
        """.format(url=url))
        try:
            with httpimport.remote_repo(url):
                import test_package

        except RuntimeError:
            pass  # <--- zipfile module fails for wrong password

        self.assertFalse('test_package' in sys.modules)

    def test_github_repo(self):
        print("[+] Importing from GitHub")
        with httpimport.github_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_bitbucket_repo(self):
        print("[+] Importing from BitBucket")
        with httpimport.bitbucket_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_gitlab_repo(self):
        print("[+] Importing from GitLab")
        with httpimport.gitlab_repo('operatorequals', 'httpimport-test', ref='main'):
            import test_package

        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_load_http(self):
        pack = httpimport.load(
            'test_package', URLS['web_dir'] % PORT)

        self.assertTrue(pack)

    def test_load_relative_fail(self):
        try:
            pack = httpimport.load(
                'test_package.b', URLS['web_dir'] % PORT)
        except ImportError:
            ''' Fails as 'load()' does not import modules in 'sys.modules'
            but relative imports rely on them
            '''
            self.assertTrue(True)

    def test_load_relative_success(self):
        url = URLS['web_dir'] % PORT
        with httpimport.remote_repo(url):
            import test_package.c

        self.assertTrue(test_package.c)

    def test_proxy_simple_HTTP(self):
        url = URLS['web_dir'] % PORT
        httpimport.set_profile("""[{url}]
proxy-url: http://127.0.0.1:{port}
        """.format(url=url, port=PROXY_PORT))

        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue(test_package)

        with httpimport.remote_repo(URLS['web_dir'] % PORT):
            import test_package.b

        self.assertTrue(test_package.b.mod.module_name()
                        == test_package.b.mod2.mod2val)

    def test_dependent_load(self):
        pack = httpimport.load(
            'dependent_package', URLS['web_dir'] % PORT)
        self.assertTrue(pack)


test_servers._run_webservers(
    web_dir="test_web_directory",
    http_port=PORT,
    proxy_port=PROXY_PORT,
    basic_auth_port=BASIC_AUTH_PORT,
)
