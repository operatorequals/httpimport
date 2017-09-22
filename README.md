# httpimport
Module for _remote_ _in-memory_ Python _package/module_ loading _through HTTP/S_

[![PyPI version](https://badge.fury.io/py/httpimport.svg)](https://pypi.python.org/pypi/httpimport)

A feature that _Python2/3_ misses and has become popular in other languages is the remote load of packages/modules.

The `httpimport` module lets a developer to remotely import any package/module through plain HTTP or HTTPS.

### Example

Using the `SimpleHTTPServer`, a whole directory can be served through HTTP as follows:

```bash
user@hostname:/tmp/test_directory$ ls -R
.:
test_package

./test_package:
__init__.py  __init__.pyc  module1.py  module2.py
user@hostname:/tmp/test_directory$python -m SimpleHTTPServer &
[1] 9565
Serving HTTP on 0.0.0.0 port 8000 ...

user@hostname:/tmp/test_directory$
user@hostname:/tmp/test_directory$
user@hostname:/tmp/test_directory$ curl http://localhost:8000/test_package/module1.py
127.0.0.1 - - [22/Aug/2017 17:42:49] "GET /test_package/module1.py HTTP/1.1" 200 -


def dummy_func() : return 'Function Loaded'


class dummy_class :

	def dummy_method(self) : return 'Class and method loaded'


dummy_str = 'Constant Loaded'

user@hostname:/tmp/test_directory$
user@hostname:/tmp/test_directory$ curl http://localhost:8000/test_package/__init__.py
127.0.0.1 - - [22/Aug/2017 17:45:20] "GET /test_package/__init__.py HTTP/1.1" 200 -
__all__ = ["module1", "module2"]

```

Using this simple built-in feature of Py2/3, a custom importer can been created, that given a base URL and a list of package names, it fetches and automatically loads all modules and packages to the local namespace.


### Usage

#### Making the HTTP repo

```bash
user@hostname:/tmp/test_directory$ ls -R
.:
test_package

./test_package:
__init__.py  __init__.pyc  module1.py  module2.py

user@hostname:/tmp/test_directory$
user@hostname:/tmp/test_directory$ python -m SimpleHTTPServer
Serving HTTP on 0.0.0.0 port 8000 ...

```

### Importing Remotely
#### `add_remote_repo()` and `remove_remote_repo()`

These 2 functions will _add_ and _remove_ to the default `sys.meta_path` custom `HttpImporter` objects, given the URL they will look for packages/modules and a list of packages/modules its one can serve.

```python
>>> import test_package
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: No module named test_package
>>>
>>> from httpimport import add_remote_repo, remove_remote_repo
>>> # In the given URL the 'test_package/' is available
>>> add_remote_repo(['test_package'], 'http://localhost:8000/') #  
>>> import test_package
>>>
>>> remove_remote_repo('http://localhost:8000/')
>>> import test_package.module1
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: No module named module1

```

#### The `remote_repo()` context
_Adding_ and _removing_ Remote Repos can be a pain, _specially_ if there are packages that are available in **more than one** repos. So the `with` keyword does the trick again:

```python
>>> from httpimport import remote_repo
>>>
>>>
>>> with remote_repo(['test_package'], 'http://localhost:8000/') :
...     from test_package import module1
...
>>>
>>> from test_package import module2
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: cannot import name module2

>>> module1.dummy_str
'Constant Loaded'
>>> module1.dummy_func
<function dummy_func at 0x7f7a8a170410>
```

### The Tiny Test for your amusement

The `test.py` file contains a minimal test. Try changing working directories and package names and see what happens...

```bash
$ python test.py
serving at port 8000
127.0.0.1 - - [22/Aug/2017 17:36:44] code 404, message File not found
127.0.0.1 - - [22/Aug/2017 17:36:44] "GET /test_package/module1/__init__.py HTTP/1.1" 404 -
127.0.0.1 - - [22/Aug/2017 17:36:44] "GET /test_package/module1.py HTTP/1.1" 200 -
Constant Loaded
Function Loaded
Class and method loaded

```

## The _Github_ Use Case!

Such HTTP Servers (serving Python packages in a _directory structured way_) can be found in the wild, not only created with `SimpleHTTPServer`.
**Github repos can serve as Python HTTPS Repos as well!!!**

### Here is an example with my beloved `covertutils` project:
```python
>>>
>>> import covertutils
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: No module named covertutils
>>>	# covertutils is not available through normal import!
>>>
>>> covertutils_url = 'https://raw.githubusercontent.com/operatorequals/covertutils/master/'
>>>
>>> from httpimport import remote_repo
>>>
>>> with remote_repo(['covertutils'], covertutils_url) :
...     import covertutils
...
>>> print covertutils.__author__
John Torakis - operatorequals
```


### The **dedicated** `github_repo()` context:
```python
>>> from httpimport import github_repo
>>> with github_repo( 'operatorequals', 'covertutils', ) :
...     import covertutils
...
>>> covertutils.__author__
'John Torakis - operatorequals'
>>>
```
#### What about branches?
```python
>>> from httpimport import github_repo
>>> with github_repo( 'operatorequals', 'covertutils', branch='py3_compatibility' ) :
...     import covertutils
...
>>> covertutils.__author__
'John Torakis - operatorequals'
>>>
```

#### And ad-hoc commits too?
What if you need to stick to a fixed -_known to work_- commit?
```python
>>> from httpimport import github_repo
>>> with github_repo( 'operatorequals', 'covertutils', commit='cf3f78c77c437edf2c291bd5b4ed27e0a93e6a77' ) :
...     import covertutils
...
>>> covertutils.__author__
'John Torakis - operatorequals'
>>>
```


#### And no data touches the disk, nor any virtual environment. The import happens just to the running Python process!
### Life suddenly got simpler for Python module testing!!!
Imagine the breeze of testing _Pull Requests_ and packages that you aren't sure they will work for you!


## Debugging...
```python
>>> from httpimport import *
>>>
>>> import logging
>>> logging.getLogger('httpimport').setLevel(logging.DEBUG)
>>>
>>> with github_repo('operatorequals','covertutils') :
...     import covertutils
...
FINDER=================
[!] Searching covertutils
[!] Path is None
[@]Checking if in domain >
[@]Checking if built-in >
[@]Checking if it is name repetition >
[*]Module/Package 'covertutils' can be loaded!
LOADER=================
[+] Loading covertutils
[+] Trying to import as package from: 'https://raw.githubusercontent.com/operatorequals/covertutils/master//covertutils/__init__.py'
[+] Importing 'covertutils'
[+] Ready to execute 'covertutils' code
[+] 'covertutils' imported succesfully!
>>>
```


## Beware: **Huge Security Implications!**
_Using the `httpimport` with **HTTP URLs** is highly discouraged outside the `localhost` interface!_
  
As HTTP traffic isn't encrypted and/or integrity checked (_unlike HTTPS_), it is trivial for a remote attacker to intercept the HTTP responses (via an _ARP MiTM_ probably), and add arbitrary _Python_ code to the downloaded _packages/modules_.
This will directly result in _Remote Code Execution_ to your current user's context! In other words, you get **totally F\*ed**...
#### You have been warned! Use **HTTPS URLs** with `httpimport`!




##### Did I hear you say "Staging protocol for [covertutils](https://github.com/operatorequals/covertutils) backdoors"?

Technique documentation on [using `httpimport` to stage `covertutils` backdoor code](http://covertutils.readthedocs.io/en/latest/staging_exec.html), making *EXE packed* and *unreadable* code load *non-included module dependencies*.
