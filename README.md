# `httpimport`
### *Python's missing feature!*

_Remote_, _in-memory_ Python _package/module_ `import`ing **through HTTP/S**

[![PyPI version](https://badge.fury.io/py/httpimport.svg)](https://pypi.python.org/pypi/httpimport)

A feature that _Python2/3_ **misses** and has become popular in other languages is the **remote loading of packages/modules**.

`httpimport` lets a *Python2/3* packages/modules to be imported directly in Python interpreter's process memory, through **remote `URIs`**, and *more*...

### Example - In a Nutshell

```python
>>> import httpimport
>>> httpimport.__all__
['HttpImporter', 'add_remote_repo', 'remove_remote_repo', 'remote_repo', 'github_repo', 'bitbucket_repo']
```
```python
>>> with httpimport.remote_repo(['package1','package2','package3'], 'http://my-codes.example.com/python_packages'):
... 	import package1
...
```
```python
>>> with httpimport.github_repo('operatorequals', 'covertutils', branch = master):
...     import covertutils
... # Also works with 'bitbucket_repo'
```
```python
>>> # A depends to B and B depends to C (A, B, C : Python modules/packages in different domains):
>>> # A exists in "repo_a.my-codes.example.com"	|
>>> # B exists in "repo_b.my-codes.example.com" | <-- Different domains
>>> # C exists in "repo_c.my-codes.example.com" |
>>> with httpimport.remote_repo(['C'], 'http://repo_c.my-codes.example.com/python_packages'):
...	 with httpimport.remote_repo(['B'], 'http://repo_b.my-codes.example.com/python_packages'):
...		with httpimport.remote_repo(['A'], 'http://repo_a.my-codes.example.com/python_packages'):
... 	import A
... # Asks for A, Searches for B, Asks for B, Searches for C, Asks for C --> Resolves --> Imports A
>>>
```
```python
>>> module_object = httpimport.load('package1', 'http://my-codes.example.com/python_packages')
>>> module_object
<module 'package1' from 'http://my-codes.example.com/python_packages/package1/__init__.py'>
```

### Example - The Whole Picture 

Using the `SimpleHTTPServer`, a whole directory can be served through HTTP as follows:

```bash
user@hostname:/tmp/test_directory$ ls -R
.:
test_package

./test_package:
__init__.py  __init__.pyc  module1.py  module2.py
user@hostname:/tmp/test_directory$
user@hostname:/tmp/test_directory$ python -m SimpleHTTPServer &
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

Using this simple built-in feature of `Py2/3`, a custom importer can been created, that given a base URL and a list of package names, it fetches and automatically loads all modules and packages to the local namespace.


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

### Reload module (setting `httpimport.RELOAD` flag):
```python
import importlib
import httpimport

httpimport.INSECURE = True

with httpimport.remote_repo(['mod'], 'http://localhost:8000/a'):
    import mod
    print(mod.module_name())

with httpimport.remote_repo(['mod'], 'http://localhost:8000/b'):
    importlib.reload(mod)
    import mod
    print(mod.module_name())

httpimport.RELOAD = True  # Allow reload module

with httpimport.remote_repo(['mod'], 'http://localhost:8000/b'):
    importlib.reload(mod)
    import mod
    print(mod.module_name())
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

### Here is an example with my beloved ``covertutils`` project:
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
### The newer sibling `bitbucket_repo()` (as of `0.5.9`)
```python
>>> with bitbucket_repo('atlassian', 'python-bitbucket', module='pybitbucket'):
...     import pybitbucket
...
>>>
```

### Another sibling `gitlab_repo()` (as of `0.5.17`)
```python
>>> with gitlab_repo('harinathreddyk', 'python-gitlab', module='gitlab'):
...     from gitlab import const
...
>>>
```

#### The `domain` parameter for `gitlab_repo()`
You can point to your own installation of *GitLab* by using the `domain` parameter:

```python
>>> with gitlab_repo('self', 'myproject', module='test_package', domain='127.0.0.1:8080'):
...     import test_package
...
>>>
```
This covers the posibility of using `httpimport` to point development environments,
which is a strong use case for `httpimport`.


## Recursive Dependencies
If package `A` requires module `B` and `A` exists in `http://example.com/a_repo/`, while `B` exists in `http://example.com/b_repo/`, then `A` can be imported using the following technique:
```python
>>> from httpimport import remote_repo
>>> with remote_repo(['B'],"http://example.com/b_repo/") :
...     with remote_repo(['A'],"http://example.com/a_repo/") :
...             import A
... 
[!] 'B' not found in HTTP repository. Moving to next Finder.
>>> 
>>> A
<module 'A' from 'http://example.com/a_repo/A/__init__.py'>
>>> B
<module 'B' from 'http://example.com/a_repo/B.py'>
>>> 
```
Any combination of *packages* and *modules* can be imported this way!

*The `[!]` Warning was emitted by the `HttpImporter` object created for `A`, as it couldn't locate `B`, and passed control to the next `Finder` object, that happened to be the `HttpImporter` object created for `B`!*

## The `load()` function (as of `0.5.10`)
The `load()` function was added to make module loading possible without `Namespace` pollution.
```python
>>> import httpimport
>>> pack1 = httpimport.load('random-package','http://localhost:8000/')
>>> pack1
<module 'random-package' from 'http://localhost:8000//random-package/__init__.py'>
>>>
>>> # Trying to load 'os' module from the URL will fail, as it won't delegate to to other Finders/Loaders.
>>> httpimport.load('os','http://localhost:8000/')
[!] 'non-existent-package' not found in HTTP repository. Moving to next Finder.
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "httpimport.py", line 287, in load
    raise ImportError("Module '%s' cannot be imported from '%s'" % (module_name, url) )
ImportError: Module 'os' cannot be imported from 'http://localhost:8000/'
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
[@] Checking if connection is HTTPS secure >
[@] Checking if in declared remote module names >
[@] Checking if built-in >
[@] Checking if it is name repetition >
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

### Preventing the disaster (setting `httpimport.INSECURE` flag):
```python
>>> import httpimport
>>>
>>> # Importing from plain HTTP ...
>>> httpimport.load('test_module', 'http://localhost:8000//')
[!] Using non HTTPS URLs ('http://localhost:8000//') can be a security hazard!
[-] 'httpimport.INSECURE is not set! Aborting...
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "httpimport.py", line 302, in load
    raise ImportError("Module '%s' cannot be imported from URL: '%s'" % (module_name, url) )
ImportError: Module 'test_module' cannot be imported from URL: 'http://localhost:8000/'
>>> # ... Throws Error!
>>>
>>> # Importing from plain HTTP has to be DELIBERATELY enabled!
>>> httpimport.INSECURE = True
>>> httpimport.load('test_module', 'http://localhost:8000//')
[!] Using non HTTPS URLs ('http://localhost:8000//') can be a security hazard!
<module 'test_module' from 'http://localhost:8000//test_module.py'>
>>> # Succeeded!
```

#### You have been warned! Use **HTTPS URLs** with `httpimport`!


#### Did I hear you say "Staging protocol for [covertutils](https://github.com/operatorequals/covertutils) backdoors"?

Technique documentation on [using `httpimport` to stage `covertutils` backdoor code](http://covertutils.readthedocs.io/en/latest/staging_exec.html), making *EXE packed* and *unreadable* code load *non-included module dependencies*.
