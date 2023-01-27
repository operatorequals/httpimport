import httpimport
from tests import (BASIC_AUTH_CREDS, BASIC_AUTH_PROXY_PORT, HTTP_PORT,
                   PROXY_PORT, URLS, SERVER_HOST, servers, HttpImportTest)

URL = URLS['web_dir'] % HTTP_PORT


class TestBase(HttpImportTest):

    def setUp(self):
        # Initialize Content Server and Proxy
        servers.init('httpd')
        servers.init('httpd_proxy')
        servers.init('httpd_basic_auth_proxy')
        # Allow plaintext (HTTP) for all test communications
        httpimport.set_profile('''[{url}]
allow-plaintext: yes
        '''.format(url=URL))

    def test_proxy_simple_HTTP(self):
        httpimport.set_profile("""[{url}]
proxy-url: http://{host}:{port}
        """.format(host=SERVER_HOST, url=URL, port=PROXY_PORT))

        with httpimport.remote_repo(URL):
            import test_package

        self.assertTrue(test_package)

    def test_basic_auth_proxy_HTTP(self):
        httpimport.set_profile("""[{url}]
headers:
    Authorization: Basic {b64_creds}

proxy-url: http://{host}:{port}
        """.format(host=SERVER_HOST, url=URL, b64_creds=BASIC_AUTH_CREDS, port=BASIC_AUTH_PROXY_PORT))
        with httpimport.remote_repo(URL):
            import test_package
        self.assertTrue(test_package)
