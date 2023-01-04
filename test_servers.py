
try:
    # python 2
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer as BaseHTTPServer
    from urllib2 import urlopen, HTTPError
except ImportError:
    # python 3
    from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
    from urllib.request import urlopen
    from urllib.error import HTTPError

from threading import Thread
from time import sleep
import os


# Taken from:
# https://stackoverflow.com/questions/39801718/how-to-run-a-http-server-which-serve-a-specific-path
class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

# Taken from:
# https://github.com/operatorequals/httpimport/pull/42
class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self, head=False):
        try:
            resp = urlopen(self.path)
            code = resp.code
        except HTTPError as he:
            code = he.code
        self.send_response(code)
        self.end_headers()
        if code == 200 and not head:
            self.copyfile(resp, self.wfile)

    def do_HEAD(self):
        self.do_GET(head=True)

# Taken from:
# https://gist.github.com/mauler/593caee043f5fe4623732b4db5145a82
class HTTPBasicAuthHandler(HTTPHandler):
    _auth = 'dXNlcm5hbWU6cGFzc3dvcmQ='  # username:password

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="HttpImport Test"')
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        """ Present frontpage with user authentication. """
        if self.headers.get("Authorization") is None:
            self.do_AUTHHEAD()
            self.wfile.write(b"no auth header received")
        elif self.headers.get("Authorization") == "Basic " + self._auth:
            HTTPHandler.do_GET(self)
        else:
            self.do_AUTHHEAD()
            self.wfile.write(b"not authenticated")


class HTTPServer(BaseHTTPServer):
    def __init__(self, base_path, server_address,
                 RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        self.port = server_address[1]
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)

########### ###########


def _run_webservers(
    web_dir="test_web_directory",
    http_port=8000,
    proxy_port=8080,
    basic_auth_port=8001,
):

    servers = {
        'httpd': HTTPServer(web_dir, ("", http_port), RequestHandlerClass=HTTPHandler),
        'httpd_proxy': HTTPServer(web_dir, ("", proxy_port), RequestHandlerClass=ProxyHandler),
        'httpd_basic_auth': HTTPServer(web_dir, ("", basic_auth_port), RequestHandlerClass=HTTPBasicAuthHandler),
    }
    threads = {}

    for name, server in servers.items():
        print("'%s' at port %d" % (name, server.port))
        threads[name] = Thread(target=server.serve_forever, )
        threads[name].daemon = True
        threads[name].start()

    # Wait for everything to hopefully setup
    sleep(1)
