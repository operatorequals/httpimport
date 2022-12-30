try:
    import SimpleHTTPServer
    import SocketServer
    from urllib2 import urlopen
except ImportError:
    import http.server
    import socketserver
    from urllib.request import urlopen

import sys
import os

from threading import Thread
from time import sleep

import httpimport

import unittest
from random import randint

import logging
logging.getLogger('httpimport').setLevel(logging.DEBUG)


class Test(unittest.TestCase):

    PORT = 8000
    PROXY_PORT = 8080

    def tearDown(self):
        if 'dependent_module' in sys.modules:
            del sys.modules['dependent_module']
        if 'test_package' in sys.modules:
            del sys.modules['test_package']
        if 'test_package.a' in sys.modules:
            del sys.modules['test_package.a']
        if 'test_package.b' in sys.modules:
            del sys.modules['test_package.b']
        # print(sys.meta_path)
        # print (sys.modules.keys())

    def test_simple_HTTP(self):
        httpimport.INSECURE = True
        #base package import
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            import test_package
        self.assertTrue(test_package)
        #subpackage with local imports
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            import test_package.b
        self.assertTrue(test_package.b.mod.module_name() == test_package.b.mod2.mod2val)

    def test_simple_HTTP_pre_0_9_0(self):
        httpimport.INSECURE = True
        #base package import
        with httpimport.remote_repo("test_package", base_url='http://localhost:%d/' % self.PORT):
            import test_package
        self.assertTrue(test_package)

    def test_dependent_HTTP(self):
        httpimport.INSECURE = True
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            import dependent_module
        self.assertTrue(dependent_module)

    def test_simple_HTTP_fail(self):
        httpimport.INSECURE = True
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            try:
                import test_package_nonexistent
            except (ImportError, KeyError) as e:
                self.assertTrue(e)

    def test_zip_import(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.zip' % self.PORT,
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    def test_tarbz2_import(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.tar.bz2' % self.PORT,
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    def test_autodetect_corrupt_file(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        try:
            with httpimport.remote_repo(
                base_url='http://localhost:%d/test_package.corrupted.tar' % self.PORT,
            ):
                import test_package
        except (ImportError, KeyError) as e:
            self.assertTrue(e)
        # If this point is reached then the module1 is imported succesfully!
        self.assertFalse('test_package' in sys.modules)

    def test_tarxz_import(self):
        self.assertFalse('test_package' in sys.modules)
        if httpimport.LEGACY:  # Pass the test in Python2, which does not support tar.xz lzma
            self.assertTrue(True)
            return
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.tar.xz' % self.PORT,
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    def test_targz_import(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.tar.gz' % self.PORT,
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    def test_tar_import(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.tar' % self.PORT,
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    # Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
    def test_zip_import_w_pwd(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        with httpimport.remote_repo(
            base_url='http://localhost:%d/test_package.enc.zip' % self.PORT,
            zip_pwd=b'P@ssw0rd!'  # <--- Correct Password
        ):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue('test_package' in sys.modules)

    # Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
    def test_enc_zip_import_w_pwd_wrong(self):
        self.assertFalse('test_package' in sys.modules)
        httpimport.INSECURE = True
        try:
            with httpimport.remote_repo(
                base_url='http://localhost:%d/test_package.enc.zip' % self.PORT,
                zip_pwd=b'XXXXXXXX'  # <--- Wrong Password
            ):
                import test_package
        except RuntimeError:
            pass  # <--- zipfile module fails for wrong password

        # If this point is reached then the module1 is imported succesfully!
        self.assertFalse('test_package' in sys.modules)

    def test_github_repo(self):
        print("[+] Importing from GitHub")
        with httpimport.github_repo('operatorequals', 'httpimport-test', module='test_package', branch='main'):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_bitbucket_repo(self):
        print("[+] Importing from BitBucket")
        with httpimport.bitbucket_repo('operatorequals', 'httpimport-test', module='test_package', branch='main'):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_gitlab_repo(self):
        print("[+] Importing from GitLab")
        with httpimport.gitlab_repo('operatorequals', 'httpimport-test', module='test_package', branch='main'):
            import test_package
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue(test_package)
        del sys.modules['test_package']

    def test_load_http(self):
        httpimport.INSECURE = True
        pack = httpimport.load(
            'test_package', 'http://localhost:%d/' % self.PORT)
        # If this point is reached then the module1 is imported succesfully!
        self.assertTrue(pack)

    def test_proxy_simple_HTTP(self):
        httpimport.INSECURE = True
        httpimport.PROXY = {'http':'http://localhost:%d' % self.PROXY_PORT}
#        #base package import
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            import test_package
        self.assertTrue(test_package)
        #subpackage with local imports
        with httpimport.remote_repo(base_url='http://localhost:%d/' % self.PORT):
            import test_package.b
        self.assertTrue(test_package.b.mod.module_name() == test_package.b.mod2.mod2val)


#  def test_dependent_http(self) :
#    httpimport.INSECURE = True
#    pack = httpimport.load('dependent_module', 'http://localhost:%d/' % self.PORT)
#    self.assertTrue(pack)  # If this point is reached then the module1 is imported succesfully!


# ============== Setting up an HTTP server at 'http://localhost:8001/' in current directory
def _run_webserver():

    # https://stackoverflow.com/questions/39801718/how-to-run-a-http-server-which-serve-a-specific-path
    try:
        # python 2
        from SimpleHTTPServer import SimpleHTTPRequestHandler
        from BaseHTTPServer import HTTPServer as BaseHTTPServer
        from SocketServer import ThreadingTCPServer
    except ImportError:
        # python 3
        from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
        from socketserver import ThreadingTCPServer

    class HTTPHandler(SimpleHTTPRequestHandler):
        """This handler uses server.base_path instead of always using os.getcwd()"""

        def translate_path(self, path):
            path = SimpleHTTPRequestHandler.translate_path(self, path)
            relpath = os.path.relpath(path, os.getcwd())
            fullpath = os.path.join(self.server.base_path, relpath)
            return fullpath

    class HTTPServer(BaseHTTPServer):
        """The main server, you pass in base_path which is the path you want to serve requests from"""

        def __init__(self, base_path, server_address, RequestHandlerClass=HTTPHandler):
            self.base_path = base_path
            BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)

    web_dir = "test_web_directory"
    httpd = HTTPServer(web_dir, ("", Test.PORT))

    print("Serving at port %d" % Test.PORT)
    http_thread = Thread(target=httpd.serve_forever, )
    http_thread.daemon = True

    # ============== Starting the HTTP server
    http_thread.start()
    # ============== Wait until HTTP server is ready
    sleep(1)

    class HTTPProxy(SimpleHTTPRequestHandler):
        "Proxy class for testing proxied urlopen()s"
        def do_GET(self):
            url = self.path
            try:
                url_check = urlopen(url)
                self.send_response(200)
                self.send_header('Content-Type',url_check.headers['Content-Type'])
                self.end_headers()
                self.copyfile(urlopen(url), self.wfile)
            except:
                self.send_response(404)
                self.end_headers()

    httpd_proxy = ThreadingTCPServer(('', Test.PROXY_PORT), HTTPProxy)
    print("Proxy Serving at port %d" % Test.PROXY_PORT)
    proxy_thread = Thread(target=httpd_proxy.serve_forever, )
    proxy_thread.daemon = True

    # ============== Starting the HTTP Proxy server
    proxy_thread.start()
    # ============== Wait until HTTP Proxy server is ready
    sleep(1)


_run_webserver()
# while True:
#   sleep(1)
