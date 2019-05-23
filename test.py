try :
	import SimpleHTTPServer
	import SocketServer
except ImportError:
	import http.server
	import socketserver

import sys

from threading import Thread
from time import sleep

import httpimport

import unittest
from random import randint


class Test( unittest.TestCase ) :

	def test_simple_HTTP(self) :
		# ============== Setting up an HTTP server at 'http://localhost:8001/' in current directory
		try :
			PORT = int(sys.argv[1])
		except :
			PORT = randint(1025, 65535)

		try :
			Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
			httpd = SocketServer.TCPServer(("", PORT), Handler)
		except :
			Handler = http.server.SimpleHTTPRequestHandler
			httpd = socketserver.TCPServer(("", PORT), Handler)
			
		print ("Serving at port %d" % PORT)

		http_thread = Thread( target = httpd.serve_forever, )
		http_thread.daemon = True

		# ============== Starting the HTTP server
		http_thread.start()

		# ============== Wait until HTTP server is ready
		sleep(1)
		httpimport.INSECURE = True
		with httpimport.remote_repo(['test_package'], base_url = 'http://localhost:%d/' % PORT) :
			from test_package import module1

		self.assertTrue(module1.dummy_str)	# If this point is reached then the module1 is imported succesfully!


	def test_github_repo(self) :
		with httpimport.github_repo( 'operatorequals', 'covertutils', ) :
			import covertutils
		self.assertTrue(covertutils.__author__)	# If this point is reached then the module1 is imported succesfully!

