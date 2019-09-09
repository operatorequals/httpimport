try :
	import SimpleHTTPServer
	import SocketServer
except ImportError:
	import http.server
	import socketserver

import sys, os

from threading import Thread
from time import sleep

import httpimport

import unittest
from random import randint


class Test( unittest.TestCase ) :

	def tearDown(self):
		if 'test_package' in sys.modules:
			del sys.modules['test_package']
		if 'test_package.a' in sys.modules:
			del sys.modules['test_package.a']
		if 'test_package.b' in sys.modules:
			del sys.modules['test_package.b']

			print (sys.modules.keys())

	PORT=8000


	# def __init__(self)


	# def test_simple_HTTP(self) :
	# 	self._run_webserver()
	# 	httpimport.INSECURE = True
	# 	with httpimport.remote_repo(['test_package'], base_url = 'http://localhost:%d/' % self.PORT) :
	# 		from test_package import module1

	# 	self.assertTrue(module1.dummy_str)	# If this point is reached then the module1 is imported succesfully!


	def test_zip_import(self):
		self.assertFalse('test_package' in sys.modules)
		httpimport.INSECURE = True
		with httpimport.remote_repo(
			['test_package'],
			base_url = 'http://localhost:%d/test_package.zip' % self.PORT,
			zip=True
			):
			import test_package
		self.assertTrue('test_package' in sys.modules)	# If this point is reached then the module1 is imported succesfully!
		del sys.modules['test_package']

	# Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
	def test_zip_import_w_pwd(self):
		self.assertFalse('test_package' in sys.modules)
		httpimport.INSECURE = True
		with httpimport.remote_repo(
			['test_package'],
			base_url = 'http://localhost:%d/test_package.enc.zip' % self.PORT,
			zip=True,
			zip_pwd=b'P@ssw0rd!'#	<--- Correct Password
			):
			import test_package
		self.assertTrue('test_package' in sys.modules)	# If this point is reached then the module1 is imported succesfully!
		del sys.modules['test_package']

	# Correct Password for 'test_package.enc.zip' 'P@ssw0rd!'
	def test_enc_zip_import_w_pwd_wrong(self):
		self.assertFalse('test_package' in sys.modules)
		httpimport.INSECURE = True
		try:
			with httpimport.remote_repo(
				['test_package'],
				base_url = 'http://localhost:%d/test_package.enc.zip' % self.PORT,
				zip=True,
				zip_pwd=b'XXXXXXXX'	#	<--- Wrong Password
				):
				import test_package
		except RuntimeError:
			pass # <--- zipfile module fails for wrong password

		self.assertFalse('test_package' in sys.modules)	# If this point is reached then the module1 is imported succesfully!


	def test_github_repo(self) :
		print ("[+] Importing from GitHub")
		with httpimport.github_repo( 'operatorequals', 'covertutils', ) :
			import covertutils
		self.assertTrue(covertutils)	# If this point is reached then the module1 is imported succesfully!
		del sys.modules['covertutils']


	def test_bitbucket_repo(self) :
		print ("[+] Importing from BiBucket")
		with httpimport.bitbucket_repo('atlassian', 'python-bitbucket', module = 'pybitbucket'):
		    import pybitbucket

		self.assertTrue(pybitbucket)
		del sys.modules['pybitbucket']


# 	def test_gitlab_repo(self) :
# 		print ("[+] Importing from GitLab")
# # https://gitlab.kwant-project.org/kwant/kwant
# 		with httpimport.gitlab_repo('kwant', 'kwant'):
# 			import kwant
# 		# with httpimport.gitlab_repo('harinathreddyk', 'python-gitlab', module='gitlab'):
# 		# 	from gitlab import const as gitlab
# 		self.assertTrue(kwant)


def _run_webserver():
	# ============== Setting up an HTTP server at 'http://localhost:8001/' in current directory

	try :
		Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
		httpd = SocketServer.TCPServer(("", Test.PORT), Handler)
	except :
		Handler = http.server.SimpleHTTPRequestHandler
		httpd = socketserver.TCPServer(("", Test.PORT), Handler)
		
	print ("Serving at port %d" % Test.PORT)
	http_thread = Thread( target = httpd.serve_forever, )
	http_thread.daemon = True

	# ============== Starting the HTTP server
	http_thread.start()
	# ============== Wait until HTTP server is ready
	sleep(1)


_run_webserver()