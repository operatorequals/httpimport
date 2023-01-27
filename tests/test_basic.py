from urllib.error import HTTPError
from urllib.request import urlopen

import httpimport
from tests import PYTHON, TEST_MODULES, URLS, HttpImportTest, HTTP_PORT
from tests import servers

URL = URLS['web_dir'] % HTTP_PORT


class TestBasic(HttpImportTest):

    def setUp(self):
        # Initialize Content Server and Proxy
        servers.init('httpd')
        # Allow plaintext (HTTP) for all test communications
        httpimport.set_profile('''[{url}]
allow-plaintext: yes
        '''.format(url=URL))

    def test_base_package(self):
        # base package import
        with httpimport.remote_repo(URL):
            import test_package
        self.assertTrue(test_package)

    def test_sub_package(self):
        with httpimport.remote_repo(URL):
            import test_package.b
        self.assertTrue(test_package.b.mod.module_name()
                        == test_package.b.mod2.mod2val)

    def test_dependent_package(self):
        with httpimport.remote_repo(URL):
            import dependent_package
        self.assertTrue(dependent_package)

    def test_nonexistent_package(self):
        with httpimport.remote_repo(URL):
            try:
                import test_package_nonexistent
            except (ImportError, KeyError) as e:
                self.assertTrue(e)

    def test_from_keyword(self):
        with httpimport.remote_repo(URL):
            from test_package import a
        self.assertTrue(a)

    def test_relative_import(self):
        with httpimport.remote_repo(URL):
            import test_package.c
        self.assertTrue(test_package.c)
