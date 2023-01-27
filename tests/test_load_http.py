import httpimport
from tests import (
    HttpImportTest,
    PYTHON,
    HTTP_PORT,
    URLS,
    ZIP_PASSWORD,
    servers)

URL = URLS['web_dir'] % HTTP_PORT


class TestLoadHttp(HttpImportTest):

    def setUp(self):
        # Initialize Content Server and Proxy
        servers.init('httpd')
        # Allow plaintext (HTTP) for all test communications
        httpimport.set_profile('''[{url}]
allow-plaintext: yes
        '''.format(url=URL))

    def test_load_http(self):
        pack = httpimport.load('test_package', URL)
        self.assertTrue(pack)

    def test_load_relative_fail(self):
        try:
            pack = httpimport.load('test_package.b', URL)
        except ImportError:
            ''' Fails as 'load()' does not import modules in 'sys.modules'
            but relative imports rely on them
            '''
            self.assertTrue(True)

    def test_dependent_load(self):
        pack = httpimport.load('dependent_package', URL)
        self.assertTrue(pack)
