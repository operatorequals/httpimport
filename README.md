# httpimport
## *Python's missing feature!*
##### [The feature has been suggested in Python Mailing List](https://lwn.net/Articles/732194/)

_Remote_, _in-memory_ Python _package/module_ `import`ing **through HTTP/S**

[![Downloads](https://img.shields.io/pypi/dm/httpimport)](https://pypi.org/project/httpimport/)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/httpimport)
[![PyPI version](https://badge.fury.io/py/httpimport.svg?cache=1)](https://pypi.python.org/pypi/httpimport)
[![Python package](https://github.com/operatorequals/httpimport/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/operatorequals/httpimport/actions/workflows/python-package.yml)

![CPython 3](https://img.shields.io/badge/Works%20on-CPython%203-brightgreen)
![Pypy 3.6](https://img.shields.io/badge/Works%20on-Pypy%203-yellowgreen)

A feature that _Python_ **misses** and has become popular in other languages is the **remote loading of packages/modules**.

`httpimport` lets Python packages and modules to be *installed* and *imported* directly in Python interpreter's process memory, through **remote `URIs`**, and *more*...

#### **Python2 support has been discontinued**. Last version that supports Python2 is [`1.1.0`](https://pypi.org/project/httpimport/1.1.0/).

## Basic Usage

### Load package/module accessible through any HTTP/S location
```python
with httpimport.remote_repo('http://my-codes.example.com/python_packages'):
  import package1
```

### Load a module from PyPI:
```python
with httpimport.pypi_repo():
  import distlib # https://pypi.org/project/distlib/

print(distlib.__version__)
# '0.3.6' <-- currently latest (https://github.com/pypa/distlib/blob/0.3.6/distlib/__init__.py#L9)
```

### Load directly from a GitHub/BitBucket/GitLab repo
```python
with httpimport.github_repo('operatorequals', 'httpimport', ref='master'):
  import httpimport as httpimport_upstream
  # Also works with 'bitbucket_repo' and 'gitlab_repo'
```

### Load a Python module from a Github Gist (using [this gist](https://gist.github.com/operatorequals/ee5049677e7bbc97af2941d1d3f04ace)):
```python
url = "https://gist.githubusercontent.com/operatorequals/ee5049677e7bbc97af2941d1d3f04ace/raw/e55fa867d3fb350f70b2897bb415f410027dd7e4"

with httpimport.remote_repo(url):
  import hello

hello.hello()
# Hello world
```

### Load a package/module directly to a variable
```python
# From HTTP/S URL
http_module = httpimport.load('package1', 'https://my-codes.example.com/python_packages')
print(http_module)
<module 'package1' from 'https://my-codes.example.com/python_packages/package1/__init__.py'>

# From PyPI
pypi_module = httpimport.load('distlib', importer_class=httpimport.PyPIImporter)
print(pypi_module)
<module 'distlib' from 'https://files.pythonhosted.org/packages/76/cb/6bbd2b10170ed991cf64e8c8b85e01f2fb38f95d1bc77617569e0b0b26ac/distlib-0.3.6-py2.py3-none-any.whl#distlib/__init__.py'>
```

### Load Python packages from archives served through HTTP/S
*No file is touching the disk in the process*
```python
# with httpimport.remote_repo('https://example.com/packages.tar'):
# with httpimport.remote_repo('https://example.com/packages.tar.bz2'):
# with httpimport.remote_repo('https://example.com/packages.tar.gz'):
# with httpimport.remote_repo('https://example.com/packages.tar.xz'): <-- Python3 Only
with httpimport.remote_repo('https://example.com/packages.zip'):
  import test_package
```

## Serving a package through HTTP/S
Any package can be served for `httpimport` using a simple HTTP/S Server:
```bash
echo 'print("Hello httpimport!")' > module.py
python -m http.server
Serving HTTP on 0.0.0.0 port 8000 ...

```

```python
>>> import httpimport
>>> with httpimport.remote_repo("http://127.0.0.1:8000"):
...   import module
...
Hello httpimport!
```

## Profiles
After `v1.0.0` it is possible to set HTTP Authentication, Custom Headers, Proxies and several other things using *URL* and *Named Profiles*!

### URL Profiles
URL Profiles are INI configurations, setting specific per-URL options, as below:

```ini
[http://127.0.0.1:8000]
allow-plaintext: yes ; also 'true' and '1' evaluate to True

[https://example.com]
proxy-url: https://127.0.0.1:8080 ; values must not be in quotes (')

```

Now, requests to `http://127.0.0.1:8000` will be allowed (HTTP URLs do not work by default) and requests to `https://example.com` will be sent to an HTTP Proxy.

```python
with httpimport.remote_repo("https://example.com"): # URL matches the URL profile
  import module_accessed_through_proxy
```
### Named Profiles
Named Profiles are like URL profiles but do not specify a URL and need to be explicitly used:

```ini
[github]
headers:
  Authorization: token <Github-Token>
```

And the above can be used as follows:

```python
with httpimport.github_repo('operatorequals','httpimport-private-test', profile='github'):
  import secret_module
```

### Profiles for PyPI
When importing from PyPI extra options can be used, as described in the profile below:

```ini
[pypi]

# The location of a 'requirements.txt' file
# to use for PyPI project versions
requirements-file: requirements-dev.txt

# Inline 'requirements.txt' syntax appended
requirements:
  distlib==0.3.5
  sampleproject==3.0.0

# Only version pinning notation is supported ('==')
# with 'requirements' and 'requirements-file' options

# A map that contains 'module': 'PyPI project' tuples
# i.e: 'import sample' --> search 'sample' module at 'sampleproject' PyPI Project:
# https://pypi.org/project/sampleproject/
project-names:
  sample: sampleproject
```

The PyPI Profiles can be used exactly like all *Named Profiles*:

```python
with httpimport.pypi_repo(profile='pypi'):
  import distlib
  import sample
distlib.__version__
# '0.3.5' <-- pinned in the profile 'requirements' option
sample.__url__
# 'https://files.pythonhosted.org/packages/ec/a8/5ec62d18adde798d33a170e7f72930357aa69a60839194c93eb0fb05e59c/sampleproject-3.0.0-py3-none-any.whl#sample/__init__.py' <-- loaded from 'sampleproject'
```

Additionally, all other options cascade to PyPI profiles, such as HTTPS Proxy (HTTP proxies won't work, as PyPI is hosted with HTTPS), `headers`, etc.

##### Github Tokens look like `github_pat_<gibberish>` and can be issued here: https://github.com/settings/tokens/new

##### NOTE: The values in Profiles MUST NOT be quoted (`'`,`"`)

### Profile Creation
Profiles can be provided as INI strings to the `set_profile` function and used in all `httpimport` functions:
```python
httpimport.set_profile("""
[profile1]

proxy-url: https://my-proxy.example.com
headers:
  Authorization: Basic ...
  X-Hello-From: httpimport
  X-Some-Other: HTTP header
""")
with httpimport.remote_repo("https://code.example.com", profile='profile1'):
  import module_accessed_through_proxy
```

#### Advanced
Profiles are INI configuration strings parsed using Python [`configparser`](https://docs.python.org/3/library/configparser.html) module.

The `ConfigParser` object for `httpimport` is the global variable `httpimport.CONFIG` and can be used freely:

```python
import httpimport
httpimport.CONFIG.read('github.ini') # Read profiles from a file

with httpimport.github_repo('operatorequals','httpimport-private-test', profile='github'):
  import secret_module
```

## Default Profiles
The `httpimport` module automatically loads Profiles found in `$HOME/.httpimport.ini` and under the `$HOME/.httpimport/` directory. Profiles under `$HOME/.httpimport/` override ones found in `$HOME/.httpimport.ini`.

### Profile Options:
#### Supported
HTTP options
* `zip-password` - `v1.0.0`
* `proxy-url` - `v1.0.0`
* `headers` - `v1.0.0`
* `allow-plaintext` - `v1.0.0`
* `ca-verify` - `v1.3.0`
* `ca-file` - `v1.3.0`

PyPI-only options
* `project-names` - `v1.2.0`
* `requirements` - `v1.2.0`
* `requirements-file` - `v1.2.0`

#### Not yet (subject to change)
* `allow-compiled`

* `auth`
* `auth-type`

* `tls-cert`
* `tls-key`
* `tls-passphrase`

## Debugging...
```python
import httpimport
import logging

logging.getLogger('httpimport').setLevel(logging.DEBUG)
```

## Beware: **Huge Security Implications!**
_Using the `httpimport` with **HTTP URLs** is highly discouraged_
  
As HTTP traffic isn't encrypted and/or integrity checked (_unlike HTTPS_), it is trivial for a remote attacker to intercept the HTTP responses (via an _ARP MiTM_ probably), and add arbitrary _Python_ code to the downloaded _packages/modules_.
This will directly result in _Remote Code Execution_ on your current user's context!

In other words, you get **totally  compromised**...

##### You have been warned! Use only **HTTPS URLs** with `httpimport`!


## Contributors
* [ldsink](https://github.com/ldsink) - The `RELOAD` flag and Bug Fixes
* [lavvy](https://github.com/lavvy) - the `load()` function
* [superloach](https://github.com/superloach) - Deprecation of `imp` module in Python3 in favour of `importlib`
* [yanliakos](https://github.com/yanliakos) - Bug Fix
* [rkbennett](https://github.com/rkbennett) - Relative Imports fix, Proxy support

## Donations
In case my work helped you, you can always buy me a beer or a liter of gas [through the Internet](https://www.buymeacoffee.com/operatorequals) or in case you meet me personally.

In the second case we can talk about any video of [Internet Historian](https://www.youtube.com/@InternetHistorian) or [Ordinary Things](https://www.youtube.com/@OrdinaryThings), while listening to a [Lofi Girl Playlist](https://www.youtube.com/watch?v=jfKfPfyJRdk), like the citizens of the Internet that we are.

[![donation](https://cdn-images-1.medium.com/max/738/1*G95uyokAH4JC5Ppvx4LmoQ@2x.png)](https://www.buymeacoffee.com/operatorequals)
