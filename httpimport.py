#!/usr/bin/env python
import sys
import logging
import types
import io
import tarfile
import zipfile
import marshal
from contextlib import contextmanager

LEGACY = (sys.version_info.major == 2)
if LEGACY:
    import imp
    from ConfigParser import ConfigParser, NoSectionError
    from urllib2 import urlopen, Request, HTTPError, URLError, ProxyHandler, build_opener, install_opener
else:
    from configparser import ConfigParser, NoSectionError
    from urllib.request import urlopen, Request, ProxyHandler, build_opener, install_opener
    from urllib.error import HTTPError, URLError

# ====================== Metadata ======================

__author__ = 'John Torakis - operatorequals'
__version__ = '1.0.0'
__github__ = 'https://github.com/operatorequals/httpimport'

# ====================== Constants ======================

INSECURE = False

__GIT_SERVICE_URLS = {
    'github': {
        'url': 'https://{domain}/{user}/{repo}/{ref}/',
        'domain': 'raw.githubusercontent.com'},
    'gitlab': {
        'url': 'https://{domain}/{user}/{repo}/raw/{ref}/',
        'domain': 'gitlab.com'},
    'bitbucket': {
        'url': 'https://bitbucket.org/{user}/{repo}/raw/{ref}/',
        'domain': 'bitbucket.com'},
}

# ====================== Configuration ======================

_DEFAULT_INI_CONFIG = """
[DEFAULT]

zip-password:

proxy-url:

# Allowing HTTP can result in a Security Hazard
allow-plaintext: no

headers:
    X-HttpImport-Version: {version}
    X-HttpImport-Project: {homepage}

### Not Implemented ###
# allow-compiled: no

# auth: username:password
# auth-type: basic

# ca-verify: yes
# ca-cert: /tmp/ca.crt
# tls-cert: /tmp/tls.cert
# tls-key: /tmp/tls.key
# tls-passphrase:
""".format(version=__version__, homepage=__github__)

CONFIG = ConfigParser()
if LEGACY:
    CONFIG.readfp(io.BytesIO(_DEFAULT_INI_CONFIG))
else:
    CONFIG.read_string(_DEFAULT_INI_CONFIG)

# ====================== Logging ======================

log_level = logging.WARNING
log_format = '%(message)s'
logger = logging.getLogger(__name__)
logger.setLevel(log_level)
log_handler = logging.StreamHandler()
log_handler.setLevel(log_level)
log_formatter = logging.Formatter(log_format)
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

# ====================== HTTP abstraction ======================


def http(url, headers={}, method='GET', proxy=None):
    """ Wraps Python2/3 HTTP calls and ensures cross-compatibility

    Args:
        url (str):
        headers (dict):
        method (str):
        proxy (str):

    Returns:
        dict: A dict containing 'code', 'headers', 'body' of HTTP response
    """

    if LEGACY:
        req = Request(url, headers=headers)
        req.get_method = lambda: method.upper()
    else:
        req = Request(url, headers=headers, method=method.upper())

    if proxy:
        scheme = proxy.split(':', 1)[0]
        proxy_handler = ProxyHandler({scheme: proxy})
        proxy_opener = build_opener(proxy_handler)
        _urlopen = proxy_opener.open
    else:
        _urlopen = urlopen

    try:
        resp = _urlopen(req)
        try:  # Python2 Approach
            headers = {  # Parse Header List to Dict
                h.split(':', 1)[0].lower(): h.split(':', 1)[1].strip()
                for h in resp.info().__dict__["headers"]
            }
        except KeyError:  # Python3 Approach
            headers = {k.lower(): v for k, v in resp.info().__dict__[
                "_headers"]}

        return {'code': resp.code, 'body': resp.read(), 'headers': headers}
    except HTTPError as he:
        return {'code': he.code, 'body': b'', 'headers': {}}

# ====================== Helpers ======================


def _isHTTPS(url):
    return url.startswith('https://')


def _get_url_options(url):
    if url in CONFIG.sections():
        return dict(CONFIG.items(url))
    else:
        return dict(CONFIG.items('DEFAULT'))


def _create_paths(module_name, suffixes=['py']):
    """ Returns possible paths where a module/package could be located

    Args:
        module_name (str): The name of the module to create paths for
        suffixes (list): A list of suffixes to be appended to the possible filenames

    Returns:
        list: The list of filepaths to be queried for module/package content
    """
    module_name = module_name.replace(".", "/")
    ret = []
    for suffix in suffixes:
        ret.extend([
            "%s.%s" % (module_name, suffix),
            "%s/__init__.%s" % (module_name, suffix),
        ])
    return ret


def _retrieve_archive(content, url):
    """ Returns an ZipFile or tarfile Archive object if available

    Args:
        content (bytes): Bytes (typically HTTP Response body) to be parsed as archive

    Returns:
        object: zipfile.ZipFile, tarfile.TarFile or None (if `contents` could not be parsed)
    """
    content_io = io.BytesIO(content)
    try:
        tar = tarfile.open(fileobj=content_io, mode='r:*')
        logger.info("[+] URL: '%s' is a Tarball" % url)
        return tar
    except tarfile.ReadError:
        # logger.info("[*] URL: '%s' is not a (compressed) tarball" % url)
        pass
    try:
        zip_ = zipfile.ZipFile(content_io)
        logger.info("[+] URL: '%s' is a ZIP file" % url)
        return zip_
    except zipfile.BadZipfile:
        # logger.info("[*] Response of '%s' is not a ZIP file" % url)
        pass
    logger.info(
        "[*] URL: '%s' is not an archive. Continuing as Web Directory!" %
        (url))
    return None


def _open_archive_file(archive_obj, filepath, zip_pwd=None):
    """ Opens a file located under `filepath` from an archive

    Args:
        archive_obj (object): zipfile.ZipFile or tarfile.TarFile
        filepath (str): The path in the archive to be extracted and returned
        zip_pwd (bytes): The password of the ZipFile (if needed)

    Returns:
        bytes: The content of the extracted file
    """
    logger.info(
        "[*] Attempting extraction of '%s' from archive..." % (filepath))
    if isinstance(archive_obj, tarfile.TarFile):
        return archive_obj.extractfile(filepath).read()
    if isinstance(archive_obj, zipfile.ZipFile):
        return archive_obj.open(filepath, 'r', pwd=zip_pwd).read()

    raise ValueError("Object is not a ZIP or TAR archive")


def _retrieve_compiled(content):  # <== Not Used Yet
    try:
        # Strip the .pyc file header of Python up to 3.3
        return marshal.loads(content[8:])
    except ValueError:
        pass
    try:
        # Strip the .pyc file header of Python 3.3 and onwards (changed .pyc
        # spec)
        return marshal.loads(content[12:])
    except ValueError:
        pass

    raise ValueError("[!] Not possible to unmarshal '.pyc' file")

# ====================== Importer Class ======================


class HttpImporter(object):
    """ The class that implements the Importer API. Contains the `find_module` and `load_module` methods.
    It is better to not use this class directly, but through its wrappers ('remote_repo', 'github_repo', etc),
    that automatically load and unload this class' objects to the 'sys.meta_path' list.

    Args:
        url (str): Contains a URL that can point to an Archive -(compressed) Tar or Zip-
        or an HTTP/S / WebDAV directory (listable or not) to be queried for Python module/packages files
        zip_pwd (bytes): The password to be used for password encrypted ZIP files
        headers (dict): The HTTP Headers to be used in all HTTP requests issued by this Importer.
            Can be used for authentication, logging, etc.
        proxy (str): The URL for the HTTP proxy to be used for all requests
    """

    def __init__(self, url, zip_pwd=b'', headers={}, proxy=None, allow_plaintext=False):
        # remove trailing '/' from URL parameter
        self.url = url if not url.endswith('/') else url[:-1]
        self.modules = {}

        if not _isHTTPS(url):
            logger.warning("[-] Using HTTP URLs (%s) with 'httpimport' is a security hazard!" % (url))
            if not (allow_plaintext or INSECURE):
                logger.error(""" [*]
Using plaintext protocols needs to be enabled through 'INSECURE' global or explicitly allowed through 'allow-plaintext'!
                """)
                raise ImportError("[-] HTTP used while plaintext is not allowed")

        self.zip_pwd = zip_pwd
        self.headers = headers
        self.proxy = proxy

        # Try a request that can fail in case of connectivity issues
        resp = http(url, headers=self.headers, proxy=self.proxy,
                    method='GET')

        # Try to extract an archive from URL
        self.archive = _retrieve_archive(resp['body'], url)

    def find_module(self, fullname, path=None):
        """ Method that determines whether a module/package can be loaded through this Importer object. Part of Importer API

        Args:
            fullname (str): The name of the package/module to be searched.
            path (str): Part of the Importer API. Not used in this object.

        Returns:
          (object): This Importer object (`self`) if the module can be importer
            or `None` if the module is not available.
        """
        logger.info(
            "[*] Trying to find loadable code for module '%s', path: '%s'" %
            (fullname, path))

        paths = _create_paths(fullname)
        for path in paths:
            if self.archive is None:
                url = self.url + '/' + path
                resp = http(url, headers=self.headers, proxy=self.proxy)
                if resp['code'] == 200:
                    logger.debug(
                        "[+] Fetched Python code from '%s'. The module can be loaded!" %
                        (url))
                    self.modules[fullname] = {}
                    self.modules[fullname]['content'] = resp['body']
                    self.modules[fullname]['filepath'] = url
                    self.modules[fullname]['package'] = path.endswith(
                        '__init__.py')
                    return self
                else:
                    logger.debug(
                        "[-] URL '%s' return HTTP Status Code '%d'. Trying next URL..." %
                        (url, resp['code']))
                    continue
            else:
                try:
                    content = _open_archive_file(
                        self.archive, path, zip_pwd=self.zip_pwd)
                    logger.debug(
                        "[+] Extracted '%s' from archive. The module can be loaded!" %
                        (path))
                    self.modules[fullname] = {}
                    self.modules[fullname]['content'] = content
                    self.modules[fullname]['filepath'] = path
                    self.modules[fullname]['package'] = path.endswith(
                        '__init__.py')
                    return self
                except KeyError:
                    logger.debug(
                        "[-] Extraction of '%s' from archive failed. Trying next filepath..." %
                        (path))
                    continue
            logger.info(
                "[-] Module '%s' cannot be loaded from '%s'. Skipping..." %
                (fullname, self.url))
        # Instruct 'import' to move on to next Importer
        return None

    def _create_module(self, fullname, sys_modules=True):
        """ Method that loads module/package code into a Python Module object

        Args:
          fullname (str): The name of the module/package to be loaded
          sys_modules (bool, optional): Set to False to not inject the module into sys.modules
            It will fail for packages/modules that contain relative imports

        Returns:
          (object): Module object containing the executed code of the specified module/package

        """

        # If the module has not been found as loadable through 'find_module'
        # method (yet)
        if fullname not in self.modules:
            logger.debug(
                "[*] Module '%s' has not been attempted before. Trying to load...")
            # Run 'find_module' and see if it is loadable through this Importer
            # object
            if self.find_module(fullname) is not self:
                logger.info(
                    "[-] Module '%s' has not been found as loadable. Failing...")
                # If it is not loadable ('find_module' did not return 'self' but 'None'):
                # throw error:
                raise ImportError(
                    "Module '%s' cannot be loaded from '%s'" %
                    (fullname, self.url))

        logger.debug(
            "[*] Creating Python Module object for '%s'" % (fullname))

        if LEGACY:
            mod = imp.new_module(fullname)
        else:
            mod = types.ModuleType(fullname)

        mod.__loader__ = self
        mod.__file__ = self.modules[fullname]['filepath']
        # Set module path - get filepath and keep only the path until filename
        mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1]) + '/']
        mod.__url__ = self.modules[fullname]['filepath']

        mod.__package__ = fullname

        # Populate subpackage '__package__' metadata with parent package names
        if len(fullname.split('.')[:-1]) > 1:
            # recursively find the parent package
            pkg_name = '.'.join(fullname.split('.')[:-1])
            while sys.modules[pkg_name].__package__ != pkg_name:
                pkg_name = '.'.join(pkg_name.split('.')[:-1])
            mod.__package__ = pkg_name

        logger.debug(
            "[*] Metadata (__package__) set to '%s' for %s '%s'" %
            (mod.__package__,
             'package' if self.modules[fullname]['package'] else 'module',
             fullname))

        if sys_modules:
            sys.modules[fullname] = mod

        # Execute the module/package code into the Module object
        try:
            exec(self.modules[fullname]['content'], mod.__dict__)
        except BaseException:
            if not sys_modules:
                logger.warning(
                    "[-] Module/Package '%s' cannot be imported without adding it to sys.modules. Might contain relative imports." %
                    fullname)

        return mod

    def load_module(self, fullname):
        """ Method that loads a module into current Python Namespace. Part of Importer API

        Args:
            fullname (str): The name of the module/package to be loaded

        Returns:
            (object): Module object containing the executed code of the specified module/package

        """
        logger.info("[*] Loading module '%s' into sys.modules" % fullname)

        if LEGACY:
            imp.acquire_lock()

        try:
            mod = self._create_module(fullname)
            return sys.modules[fullname]
        finally:
            if LEGACY:
                imp.release_lock()


# ====================== Feature Helpers ======================

def __create_git_url(service, username=None, repo=None,
                     ref='master', domain=None):
    """ Function that creates a URL of a Managed Git Service. Uses the internal
      `__GIT_SERVICE_URLS` dict constant.

    Args:
      service (str): The name of the Git Managed Service (as in the keys of `__GIT_SERVICE_URLS` dict)
      username (str): The username which is the repository's owner in the Git Service.
      repo (str): The name of the repository that contains the modules/packages to be imported
      ref (str): The commit hash, branch or tag to be fetched
      domain (str): The domain to be used for the URL (service domains service raw content)

    Returns
      str: The URL of the raw contents as served by the Managed Git Service
    """
    if domain is None:
        domain = __GIT_SERVICE_URLS[service]['domain']
    url_template = __GIT_SERVICE_URLS[service]['url']
    return url_template.format(
        domain=domain, user=username, repo=repo, ref=ref)


def __extract_profile_options(url=None, profile=None):
    if profile:
        # If there is a profile name set - try it
        options = _get_url_options(profile)
        logger.debug("[*] Profile for URL: '%s' -> %s" % (url, options))
        logger.debug(
            "[*] Profile '%s' for URL: '%s' -> %s" %
            (profile, url, options))
        if url is None:
            url = options['url']
    else:
        options = _get_url_options(url)
        logger.debug("[*] Profile for URL: '%s' -> %s" % (url, options))

    proxy = options['proxy-url']

    # Python2/3 Bytes vs Str issue. Start with Python2 way, try Python3
    zip_pwd = options['zip-password']
    if not LEGACY:
        zip_pwd = bytes(options['zip-password'], 'utf8')

    # Parse header dict from str lines
    headers = {
        line.split(':', 1)[0].strip(): line.split(':', 1)[1].strip()
        for line in options['headers'].splitlines()
        if line
    }

    # Parse Plaintext Flag
    allow_plaintext = options['allow-plaintext'].lower() in ['true', 'yes', '1']
    return {'headers': headers, 'proxy': proxy, 'url': url, 'zip_pwd': zip_pwd, 'allow-plaintext': allow_plaintext}

# ====================== Features ======================


def set_profile(ini_str):
    global CONFIG
    if LEGACY:
        CONFIG.readfp(io.BytesIO(ini_str))
    else:
        CONFIG.read_string(ini_str)


def add_remote_repo(url=None, profile=None):
    """ Creates an HttpImporter object and adds it to the `sys.meta_path`.

    Args:
      url (str): The URL of an HTTP/WebDav directory (either listable or not)
    or of an archive (supported: .zip, .tar, .tar.bz, .tar.gz, .tar.xz - Python3 only)

    Returns:
      HttpImporter: The `HttpImporter` object added to the `sys.meta_path`
    """
    options = __extract_profile_options(url, profile)
    importer = HttpImporter(
        url,
        headers=options['headers'],
        proxy=options['proxy'],
        zip_pwd=options['zip_pwd'],
        allow_plaintext=options['allow-plaintext'],
        )
    sys.meta_path.append(importer)
    return importer


def remove_remote_repo(url):
    """ Removes from the 'sys.meta_path' an HttpImporter object given its HTTP/S URL.

    Args:
      url (str): The URL of the `HttpImporter` object to remove

    """
    # Remove trailing '/' in case it is there
    url = url if not url.endswith('/') else url[:-1]
    for importer in sys.meta_path:
        try:
            if importer.url.startswith(url):
                sys.meta_path.remove(importer)
                return True
        except AttributeError as e:
            pass
    return False


@contextmanager
def remote_repo(url=None, profile=None):
    """ Context Manager that provides remote import functionality through a URL

    Args:
      url (str): The URL of an HTTP/WebDav directory (either listable or not)
    or of an archive (supported: .zip, .tar, .tar.bz, .tar.gz, .tar.xz - Python3 only)

    """
    importer = add_remote_repo(url=url, profile=profile)
    url = importer.url
    try:
        yield
    except ImportError as e:
        raise e
    finally:  # Always remove the added HttpImporter from sys.meta_path
        remove_remote_repo(url)


@contextmanager
def github_repo(username=None, repo=None, ref='master',
                domain=None, profile=None):
    """ Context Manager that enables importing modules/packages from Github repositories.

    Args:
      username (str): The username which is the repository's owner in the Git Service.
      repo (str): The name of the repository that contains the modules/packages to be imported
      ref (str): The commit hash, branch or tag to be fetched
      domain (str): The domain to be used for the URL (service domains service raw content)

    """
    url = __create_git_url('github',
                           username, repo, ref=ref, domain=domain)
    add_remote_repo(url=url, profile=profile)
    try:
        yield
    except ImportError as e:
        raise e
    finally:  # Always remove the added HttpImporter from sys.meta_path
        remove_remote_repo(url)


@contextmanager
def bitbucket_repo(username=None, repo=None, ref='master',
                   domain=None, profile=None):
    """ Context Manager that enables importing modules/packages from Bitbucket repositories.

    Args:
      username (str): The username which is the repository's owner in the Git Service.
      repo (str): The name of the repository that contains the modules/packages to be imported
      ref (str): The commit hash, branch or tag to be fetched
      domain (str): The domain to be used for the URL (service domains service raw content)

    """
    url = __create_git_url('bitbucket',
                           username, repo, ref=ref, domain=domain)
    add_remote_repo(url=url, profile=profile)
    try:
        yield
    except ImportError as e:
        raise e
    finally:  # Always remove the added HttpImporter from sys.meta_path
        remove_remote_repo(url)


@contextmanager
def gitlab_repo(username=None, repo=None, ref='master',
                domain='gitlab.com', profile=None):
    """ Context Manager that enables importing modules/packages from Gitlab repositories.

    Args:
      username (str): The username which is the repository's owner in the Git Service.
      repo (str): The name of the repository that contains the modules/packages to be imported
      ref (str): The commit hash, branch or tag to be fetched
      domain (str): The domain to be used for the URL (service domains service raw content)

    """
    url = __create_git_url('gitlab',
                           username, repo, ref=ref, domain=domain)
    add_remote_repo(url=url, profile=profile)
    try:
        yield
    except ImportError as e:
        raise e
    finally:  # Always remove the added HttpImporter from sys.meta_path
        remove_remote_repo(url)


def load(module_name, url=None, profile=None):
    """ Loads a module on demand and returns it as a module object. Does NOT load it to the Namespace.
  Example:

  >>> mod = httpimport.load('test_package', url='http://localhost:8000/')
  >>> mod
  <module 'test_package' from 'http://localhost:8000/test_package/__init__.py'>
  >>>
    """
    options = __extract_profile_options(url, profile)
    importer = HttpImporter(
        url,
        headers=options['headers'],
        proxy=options['proxy'],
        zip_pwd=options['zip_pwd'],
        allow_plaintext=options['allow-plaintext'],
        )
    return importer._create_module(module_name, sys_modules=False)
    raise ImportError(
        "Module '%s' cannot be imported from URL: '%s'" % (module_name, url))


# ====================== Runtime ======================

# Load the catch-all configuration
set_profile(_DEFAULT_INI_CONFIG)

# ====================== Main ======================

if __name__ == '__main__':
    logger.warning("[-] This module cannot be called directly!")
    pass
