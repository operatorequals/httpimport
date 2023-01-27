import httpimport
from tests import (
    HttpImportTest,
    PYTHON,
    HTTP_PORT,
    URLS,
    ZIP_PASSWORD,
    servers)


class TestArchiveFiles(HttpImportTest):

    def setUp(self):
        # Initialize Content Server and Proxy
        servers.init('httpd')
        # Allow plaintext (HTTP) for all test communications
        httpimport.set_profile('''[DEFAULT]
allow-plaintext: yes
        ''')

    def test_tarbz2_import(self, url=URLS['tar_bz'] % HTTP_PORT):
        with httpimport.remote_repo(url):
            import test_package
        self.assertTrue(test_package)

    def test_autodetect_corrupt_file(
            self, url=URLS['tar_corrupt'] %
            HTTP_PORT):
        try:
            with httpimport.remote_repo(url):
                import test_package
        except (ImportError, KeyError) as e:
            self.assertTrue(e)

    def test_tarxz_import(self, url=URLS['tar_xz'] % HTTP_PORT):
        # Pass the test in IronPython, which does not support tar.xz lzma
        if PYTHON == "ironpython":
            self.assertTrue(True)
            return
        with httpimport.remote_repo(url):
            import test_package
        self.assertTrue(test_package)

    def test_targz_import(self, url=URLS['tar_gz'] % HTTP_PORT):
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue(test_package)

    def test_tar_import(self, url=URLS['tar'] % HTTP_PORT):
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue(test_package)

    def test_zip_import(self, url=URLS['zip'] % HTTP_PORT):
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue(test_package)

    # Correct Password for 'test_package.enc.zip' - 'P@ssw0rd!'
    def test_zip_import_w_pwd(self, url=URLS['zip_encrypt'] % HTTP_PORT):
        httpimport.set_profile("""[{url}]
zip-password: {password}
        """.format(url=url, password=ZIP_PASSWORD))
        with httpimport.remote_repo(url):
            import test_package

        self.assertTrue(test_package)

    def test_zip_import_w_pwd_wrong(self, url=URLS['zip_encrypt'] % HTTP_PORT):
        httpimport.set_profile("""[{url}]
# wrong password!
zip-password: XXXXXXXX
        """.format(url=url))
        try:
            with httpimport.remote_repo(url):
                import test_package

        except RuntimeError:
            self.assertTrue(True)
