import SimpleHTTPServer
import SocketServer
import sys

from threading import Thread
from time import sleep

from httpimport import remote_repo



# ============== Setting up an HTTP server at 'http://localhost:8001/' in current directory
try :
	PORT = int(sys.argv[1])
except :
	PORT = 8000

Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

httpd = SocketServer.TCPServer(("", PORT), Handler)

print "serving at port", PORT

http_thread = Thread( target = httpd.serve_forever, )
http_thread.daemon = True

# ============== Starting the HTTP server
http_thread.start()

# ============== Wait until HTTP server is ready
sleep(1)

with remote_repo(['test_package'], base_url = 'http://localhost:%d/' % PORT) :
	from test_package import module1


print ( module1.dummy_str )
print ( module1.dummy_func() )
dum_obj = module1.dummy_class()
print ( dum_obj.dummy_method() )