# `httpimport`
## *Python's missing feature!*

_Remote_, _in-memory_ Python _package/module_ `import`ing **through HTTP/S**

[![PyPI version](https://badge.fury.io/py/httpimport.svg)](https://pypi.python.org/pypi/httpimport)
[![Build Status](https://travis-ci.org/operatorequals/httpimport.svg?branch=tests)](https://travis-ci.org/operatorequals/httpimport)
https://github.com/operatorequals/httpimport/raw/tests/coverage.svg

A feature that _Python2/3_ **misses** and has become popular in other languages is the **remote loading of packages/modules**.

`httpimport` lets *Python2/3* packages and modules to be imported directly in Python interpreter's process memory, through **remote `URIs`**, and *more*...

## Examples
Load a simple package/module through HTTP/S
```python
>>> with httpimport.remote_repo(['package1','package2','package3'], 'http://my-codes.example.com/python_packages'):
... 	import package1
...
```
Load directly from a GitHub/BitBucket/GitLab repo
```python
>>> with httpimport.github_repo('operatorequals', 'covertutils', branch = 'master'):
...     import covertutils
... # Also works with 'bitbucket_repo' and 'gitlab_repo'
```
Load a package/module from HTTP/S directory directly to a variable
```python
>>> module_object = httpimport.load('package1', 'http://my-codes.example.com/python_packages')
>>> module_object
<module 'package1' from 'http://my-codes.example.com/python_packages/package1/__init__.py'>
```
Load a package/module that depends on other packages/modules in different HTTP/S directories
```python
>>> # A depends on B and B depends on C (A, B, C : Python modules/packages in different domains):
>>> # A exists in "repo_a.my-codes.example.com" |
>>> # B exists in "repo_b.my-codes.example.com" | <-- Different domains
>>> # C exists in "repo_c.my-codes.example.com" |
>>> with httpimport.remote_repo(['C'], 'http://repo_c.my-codes.example.com/python_packages'):
...  with httpimport.remote_repo(['B'], 'http://repo_b.my-codes.example.com/python_packages'):
...   with httpimport.remote_repo(['A'], 'http://repo_a.my-codes.example.com/python_packages'):
...   import A
... # Asks for A, Searches for B, Asks for B, Searches for C, Asks for C --> Resolves --> Imports A
>>>
```

### Serving a package through HTTP/S
```bash
$ ls -lR
test_web_directory/:                                                         
total 16                                                                     
drwxrwxr-x. 4 user user 4096 Sep  9 20:54 test_package                       
[...]                  
                                                                             
test_web_directory/test_package:                                             
total 20                                                                     
drwxrwxr-x. 2 user user 4096 Sep  9 20:54 a                                  
drwxrwxr-x. 2 user user 4096 Sep  9 20:54 b                                  
-rw-rw-r--. 1 user user   33 Sep  9 20:54 __init__.py                        
-rw-rw-r--. 1 user user  160 Sep  9 20:54 module1.py                         
-rw-rw-r--. 1 user user  160 Sep  9 20:54 module2.py                         
                                                                             
test_web_directory/test_package/a:                                           
total 4                                                                      
-rw-rw-r--. 1 user user  0 Sep  9 20:54 __init__.py                          
-rw-rw-r--. 1 user user 41 Sep  9 20:54 mod.py                               
                                                                             
test_web_directory/test_package/b:                                           
total 4
-rw-rw-r--. 1 user user  0 Sep  9 20:54 __init__.py
-rw-rw-r--. 1 user user 41 Sep  9 20:54 mod.py

$ python -m SimpleHTTPServer
Serving HTTP on 0.0.0.0 port 8000 ...

```

## Usage

### Importing Remotely

#### `add_remote_repo()` and `remove_remote_repo()`

These 2 functions will _add_ and _remove_ to the default `sys.meta_path` custom `HttpImporter` objects, given the URL they will look for packages/modules and a list of packages/modules its one can serve.

```python
>>> import test_package### Contexts

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

### The `load()` function (as of `0.5.10`)
The `load()` function was added to make module loading possible without `Namespace` pollution.
It is used to programmatically load a module in a variable, and call its objects directly from that variable.
```python
>>> import httpimport
>>> pack1 = httpimport.load('test_package','http://localhost:8000/')
>>> pack1
<module 'test_package' from 'http://localhost:8000//test_package/__init__.py'>
>>>
```

### Contexts

#### The `remote_repo()` context
_Adding_ and _removing_ remote repos can be a pain, _especially_ if there are packages that are available in **more than one** repos. So the `with` keyword does the trick again:

```python
>>> from httpimport import remote_repo
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

#### The _Github_ Use Case!

##### The **dedicated** `github_repo()` context:
```python
>>> from httpimport import github_repo
>>> with github_repo( 'operatorequals', 'covertutils', ) :
...     import covertutils
...
>>> covertutils.__author__
'John Torakis - operatorequals'
>>>
```
##### What about branches?
```python
>>> from httpimport import github_repo
>>> with github_repo( 'operatorequals', 'covertutils', branch='py3_compatibility' ) :
...     import covertutils
...
>>> covertutils.__author__
'John Torakis - operatorequals'
>>>
```

##### And ad-hoc commits too?
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
#### The newer sibling `bitbucket_repo()` (as of `0.5.9`)
```python
>>> with bitbucket_repo('atlassian', 'python-bitbucket', module='pybitbucket'):
...     import pybitbucket
...
>>>
```

#### Another sibling `gitlab_repo()` (as of `0.5.17`)
```python
>>> with gitlab_repo('harinathreddyk', 'python-gitlab', module='gitlab'):
...     from gitlab import const
...
>>>
```

##### The `domain` parameter for `gitlab_repo()`
You can point to your own installation of *GitLab* by using the `domain` parameter:

```python
>>> with gitlab_repo('self', 'myproject', module='test_package', domain='127.0.0.1:8080'):
...     import test_package
...
>>>
```
This covers the posibility of using `httpimport` to target local development environments,
which is a strong use case for `httpimport`.


### Import remote (encrypted) ZIP files (as of `0.5.18`)
After version `0.5.18` the `add_remote_repo` and the `load` functions,
as well as the `remote_repo` context got the `zip` and `zip_pwd` parameters.
By pointing to a HTTP/S URL containing a ZIP file, it is possible to remotely load modules/packages included in it,
*without downloading the ZIP file to disk*!
```python
>>> with httpimport.remote_repo(
...     ['test_package'], base_url='http://localhost:8000/test_package.zip',
...     zip=True
...     ):
...    import test_package
...
>>>
```
#### Using a ZIP password (`zip_pwd` parameter)
```python
>>> with httpimport.remote_repo(
...     ['test_package'], base_url='http://localhost:8000/test_package.enc.zip',
...     zip=True, zip_pwd=b'P@ssw0rd!'
...     ):
...    import test_package
...
>>>
```


*Life suddenly got simpler for Python module testing!!!*

Imagine the breeze of testing _Pull Requests_ and packages that you aren't sure they are worth your download.


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
[-] 'httpimport.INSECURE' is not set! Aborting...
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


##### This project has started to suggest stager code for HTTP/S RATs made with [covertutils](https://github.com/operatorequals/covertutils). The Documentation for minifying and using `httpimport` for such purposes can be [found here](http://covertutils.readthedocs.io/en/latest/staging_exec.html).


### Contributors

* [ldsink](https://github.com/ldsink) - The `RELOAD` flag and Bug Fixes
* [lavvy](https://github.com/lavvy) - the `load()` function
* [superloach](https://github.com/superloach) - Deprecation of `imp` module in Python3 in favour of `importlib`
