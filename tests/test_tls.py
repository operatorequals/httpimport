import urllib

import httpimport
from tests import HttpImportTest, URLS, HTTP_PORT, PROXY_HEADER, PROXY_PORT, HTTPS_PORT, PROXY_TLS_PORT
from tests import servers

URL = (URLS['web_dir'] % HTTPS_PORT).replace("http://", "https://")


class TestHttp(HttpImportTest):

    def setUp(self):
        # Initialize Content Server and Proxy
        servers.init('httpd_tls')
        # servers.init('httpd_proxy_tls')

    def test_unverified_https_profile(self):
        httpimport.set_profile("""
[no_verify]
ca-verify: false
            """)
        with httpimport.remote_repo(URL, profile='no_verify'):
            import test_package
        self.assertTrue(test_package)

    def test_unverified_https_profile_failure(self):
        httpimport.set_profile("""
[verify]
ca-verify: false
            """)
        try:
            with httpimport.remote_repo(URL, profile='verify'):
                import test_package
        except urllib.error.URLError:
            self.assertTrue(True)

    def test_unverified_https_failure(self):
        try:
            with httpimport.remote_repo(URL):
                import test_package
        except urllib.error.URLError:
            self.assertTrue(True)

    # def test_unverified_https_proxy(self):
    #     resp = httpimport.http('https://127.0.0.1:%d' % HTTPS_PORT, proxy='https://127.0.0.1:%d' % PROXY_TLS_PORT, ca_verify=False)
    #     self.assertTrue('python' in resp['headers']['server'].lower())
        