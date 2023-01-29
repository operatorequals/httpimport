#!/usr/bin/env python
import io
import json
import logging
import marshal
import os
import re
import ssl
import sys
import tarfile
import types
import zipfile
from contextlib import contextmanager
from configparser import ConfigParser, NoSectionError
from urllib.error import HTTPError, URLError
from urllib.request import (ProxyHandler, Request, build_opener,
                            install_opener, urlopen)

# ====================== Metadata ======================

__author__ = 'John Torakis - operatorequals'
__version__ = '1.3.0'
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

ca-verify: yes
ca-file:

# PyPI specific:
# A multi-line with 'requirements.txt' syntax
requirements:

# Filepath of a 'requirements.txt' file
requirements-file:

# A multi-line with (module_name, pypi_project) tuples
# e.g.:
#   bs4: beautifulsoup4
project-names:

### Not Implemented ###
# allow-compiled: no

# auth: username:password
# auth-type: basic

# tls-cert: /tmp/tls.cert
# tls-key: /tmp/tls.key
# tls-passphrase:
""".format(version=__version__, homepage=__github__)

__HOME_DIR = os.path.expanduser('~')
_DEFAULT_INI_CONFIG_FILENAME = __HOME_DIR + os.sep + ".httpimport.ini"
_DEFAULT_INI_CONFIG_DIR_NAME = __HOME_DIR + os.sep + ".httpimport"

CONFIG = ConfigParser()
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


def http(url, headers={}, method='GET', proxy=None, ca_verify=True, ca_file=None):
    """ Wraps HTTP/S calls in one place

    Args:
        url (str):
        headers (dict):
        method (str):
        proxy (str):
        ca_verify (bool):
        ca-file (str):

    Returns:
        dict: A dict containing 'code', 'headers', 'body' of HTTP response
    """
    req = Request(url, headers=headers, method=method.upper())

    if proxy:
        scheme, host = proxy.split('://', 1)
        req.set_proxy(host, scheme)

    try:
        resp = urlopen(req,
            context=ssl.create_default_context(cafile=ca_file)
                if ca_verify else ssl._create_unverified_context()
                )
        headers = {k.lower(): v for k, v in resp.getheaders()}
        return {'code': resp.code, 'body': resp.read(), 'headers': headers}
    except HTTPError as he:
        return {'code': he.code, 'body': b'', 'headers': {}}

# ====================== Helpers ======================


def _isHTTPS(url):
    return url.startswith('https://')


def _get_options(url):
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


def _create_pypi_url(
        module_name,
        version=None,
        allowed_dists=[
            'bdist_wheel',
            'sdist'],
        pypi_url="https://pypi.org/pypi/%s/json"):
    """ Returns the URL of a PyPI distribution of a module.
The Download URL is acquired by directly querying the PyPI API:
https://warehouse.pypa.io/api-reference/json.html
    """
    url = pypi_url % module_name
    logger.debug("[+] Querying PyPI URL '%s'" % url)
    try:
        raw_response = http(url)
        pypi_response = json.loads(raw_response['body'])
    except json.decoder.JSONDecodeError:
        raise ModuleNotFoundError(
            "PyPI API did not respond with JSON for '%s'. HTTP Status Code: %d" %
            (module_name, raw_response['code']))
    if version is None:
        version = pypi_response['info']['version']
    if version not in pypi_response['releases']:
        raise KeyError(
            "Version '%s' not available for module %s" %
            version, module_name)
    release = pypi_response['releases'][version]
    logger.info(
        "[+] Version '%s' found for module '%s'" %
        (version, module_name))
    for package in release:
        if 'url' not in package:
            logger.info(
                "[-] Version '%s' is an empty release for module '%s'" %
                version, module_name)
            continue
        if package['packagetype'] in allowed_dists:
            logger.info(
                "[+] Version '%s' release available in %s" %
                (version, allowed_dists))
            return package['url']
    raise KeyError(
        "No allowed release type found for %s==%s. Allowed release types: %s" %
        (module_name, version, allowed_dists))

# ====================== Importer Classes ======================


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

    def __init__(
            self,
            url,
            zip_pwd=b'',
            headers={},
            proxy=None,
            allow_plaintext=False,
            ca_verify=True, ca_file=None, **kw):
        # remove trailing '/' from URL parameter
        self.url = url if not url.endswith('/') else url[:-1]
        self.modules = {}

        if not _isHTTPS(url):
            logger.warning(
                "[-] Using HTTP URLs (%s) with 'httpimport' is a security hazard!" %
                (url))
            if not (allow_plaintext or INSECURE):
                logger.error("""[*] Using plaintext protocols needs to be enabled through 'INSECURE' global or explicitly allowed through 'allow-plaintext'!
                """)
                raise ImportError(
                    "[-] HTTP used while plaintext is not allowed")

        if not ca_verify:
            logger.warning(
                "[-] Disabling TLS Certificate verification for URL (%s) is a security hazard!" %
                (url))

        self.zip_pwd = zip_pwd
        self.headers = headers
        self.proxy = proxy
        self.ca_verify = ca_verify
        self.ca_file = ca_file

        # Try a request that can fail in case of connectivity issues
        resp = http(url, headers=self.headers, proxy=self.proxy,
                    method='GET', ca_verify=self.ca_verify, ca_file=self.ca_file)

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
                resp = http(url, headers=self.headers, proxy=self.proxy, ca_verify=self.ca_verify, ca_file=self.ca_file)
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
                    self.modules[fullname]['filepath'] = self.url + "#" + path
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
                "[*] Module '%s' has not been attempted before. Trying to load..." % fullname)
            # Run 'find_module' and see if it is loadable through this Importer
            # object
            if self.find_module(fullname) is not self:
                logger.info(
                    "[-] Module '%s' has not been found as loadable. Failing..." % fullname)
                # If it is not loadable ('find_module' did not return 'self' but 'None'):
                # throw error:
                raise ImportError(
                    "Module '%s' cannot be loaded from '%s'" %
                    (fullname, self.url))

        logger.debug(
            "[*] Creating Python Module object for '%s'" % (fullname))

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
        mod = self._create_module(fullname)
        return sys.modules[fullname]


class PyPIImporter(object):
    """ The class that implements the Importer API. Uses the HttpImporter to import PyPI
releases.

    Args:
        version_matrix (dict):
        project_matrix (dict):
        allowed_dists (list):
        pypi_url (str):
        **kw (dict): Parameters that are passed to HttpImporter objects created by this class
     """

    def __init__(
            self,
            url="https://pypi.org/pypi/%s/json",
            project_matrix={},
            version_matrix={},
            allowed_dists=[
                'bdist_wheel',
                'sdist'], **kw):
        if url is None:
            url = 'https://pypi.org/pypi/%s/json'
        self.url = url  # Duck Type with HttpImporter
        self.version_matrix = version_matrix
        self.project_matrix = project_matrix
        self.allowed_dists = allowed_dists
        self.module_importers = {}
        self.kw = kw

    def find_module(self, module_name, path=None):
        logger.info(
            "[*] Trying to find PyPI module '%s', path: '%s'" %
            (module_name, path))
        module_root = module_name.split('.')[0]
        if module_root in self.module_importers:
            return self.module_importers[module_root]

        version = None
        # Get the PyPI Project from Module name, if not available use module
        # root
        project_name = self.project_matrix.get(module_root, module_root)
        version_tuple = self.version_matrix.get(project_name, (None, None))
        # Parse version tuple ('==', '1.0.0')
        if version_tuple[0] == '==':
            version = version_tuple[1]

        try:
            url = _create_pypi_url(
                project_name,
                version=version,
                allowed_dists=self.allowed_dists,
                pypi_url=self.url)
            importer = HttpImporter(url, **self.kw)
            found = importer.find_module(module_name)
            if found:
                logger.info(
                    "[+] Module '%s' can be loaded from PyPI project '%s'. URL: '%s'" %
                    (module_name, project_name, url))
                self.module_importers[module_root] = found
                return found

        except (KeyError, ModuleNotFoundError) as e:
            logger.warning("[-] %s" % e)
        # Could not load module from PyPI
        logger.warning(
            "[-] Module '%s' cannot be found in PyPI." %
            module_name)
        return None

    def _create_module(self, fullname, sys_modules=True):
        module_root = fullname.split('.')[0]
        if module_root not in self.module_importers:
            logger.debug(
                "[*] Module '%s' has not been attempted before. Trying to find in PyPI..." % fullname)
            # Run 'find_module' and see if it returns an HttpImporter
            # object
            if type(self.find_module(fullname)) != HttpImporter:
                logger.info(
                    "[-] Module '%s' has not been found in PyPI. Failing..." % fullname)
                # If it is not loadable ('find_module' did not return HttpImporter):
                raise ImportError(
                    "Module '%s' cannot be loaded from PyPI" %
                    (fullname))
        return self.module_importers[module_root]._create_module(fullname, sys_modules)

    def load_module(self, fullname):
        logger.info(
            "[*] Loading PyPI module '%s'" %
            (fullname))
        try:
            return self._create_module(fullname)
        except KeyError:
            pass
        logger.warning(
            "[-] Module '%s' could not be imported from PyPI." %
            fullname)


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
        options = _get_options(profile)
        logger.debug("[*] Profile for URL: '%s' -> %s" % (url, options))
        logger.debug(
            "[*] Profile '%s' for URL: '%s' -> %s" %
            (profile, url, options))
        if url is None:
            # if there is no 'url' in there too, could be a PyPI profile
            url = options.get('url', None)
    else:
        options = _get_options(url)
        logger.debug("[*] Profile for URL: '%s' -> %s" % (url, options))

    proxy = options['proxy-url']
    zip_pwd = bytes(options['zip-password'], 'utf8')

    # Parse header dict from str lines
    headers = {
        line.split(':', 1)[0].strip(): line.split(':', 1)[1].strip()
        for line in options['headers'].splitlines()
        if line
    }

    # Parse allow-HTTP Flag
    allow_plaintext = options['allow-plaintext'].lower() in ['true',
                                                             'yes', '1']
    ca_verify = options['ca-verify'].lower() in ['true', 'yes', '1']

    ca_file = None if not options['ca-file'] else options['ca-file']

    # Get PyPI requirements
    requirements_file = options['requirements-file']
    requirements = options['requirements']
    # Add file requirements to requirement dict
    if requirements_file:
        with open(requirements_file) as req_file:
            requirements += '\n' + req_file.read()

    # Parse requirements
    version_matrix = {}
    for line in requirements.splitlines():
        if not line:
            continue
        match = re.match(r'^([\w_-]+)\s*(([=<>]=)\s*(\d+\.\d+\.\d+))?', line)
        if not match:
            continue

        if match.group(3, 4):
            version_matrix[match.group(1)] = (match.group(3, 4))
        else:
            version_matrix[match.group(1)] = (match.group(None))

    # Parse header dict from str lines
    project_matrix = {
        line.split(':', 1)[0].strip(): line.split(':', 1)[1].strip()
        for line in options['project-names'].splitlines()
        if line
    }

    return {
        'headers': headers,
        'proxy': proxy,
        'url': url,
        'zip_pwd': zip_pwd,
        'allow_plaintext': allow_plaintext,
        'version_matrix': version_matrix,
        'project_matrix': project_matrix,
        'ca_verify': ca_verify,
        'ca_file': ca_file
    }

# ====================== Features ======================


def set_profile(ini_str):
    global CONFIG
    CONFIG.read_string(ini_str)


def add_remote_repo(url=None, profile=None, importer_class=HttpImporter):
    """ Creates an HttpImporter object and adds it to the `sys.meta_path`.

    Args:
      url (str): The URL of an HTTP/WebDav directory (either listable or not)
    or of an archive (supported: .zip, .tar, .tar.bz, .tar.gz, .tar.xz - Python3 only)

    Returns:
      HttpImporter: The `HttpImporter` object added to the `sys.meta_path`
    """
    options = __extract_profile_options(url, profile)
    url = options.get('url', url)
    del options['url']
    logger.debug(
        "[*] Adding '%s' (profile: %s) with options: %s " %
        (importer_class, profile, options))
    importer = importer_class(
        url,
        **options,
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
    importer = add_remote_repo(
        url=url,
        profile=profile,
        importer_class=HttpImporter)
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


def load(module_name, url=None, profile=None, importer_class=HttpImporter):
    """ Loads a module on demand and returns it as a module object. Does NOT load it to the Namespace.
  Example:

  >>> mod = httpimport.load('test_package', url='http://localhost:8000/')
  >>> mod
  <module 'test_package' from 'http://localhost:8000/test_package/__init__.py'>
  >>>
    """
    options = __extract_profile_options(url, profile)
    url = options.get('url', url)
    del options['url']
    importer = importer_class(
        url,
        **options,
    )
    return importer._create_module(module_name, sys_modules=False)
    raise ImportError(
        "Module '%s' cannot be imported from URL: '%s'" % (module_name, url))

@contextmanager
def pypi_repo(url='https://pypi.org/pypi/%s/json', profile=None):
    """ Context Manager that provides remote import functionality from PyPI

    Args:
        TODO
    """
    importer = add_remote_repo(
        url=url,
        profile=profile,
        importer_class=PyPIImporter)
    url = importer.url
    try:
        yield
    except ImportError as e:
        raise e
    finally:  # Always remove the added Importer from sys.meta_path
        remove_remote_repo(url)

# ====================== Runtime ======================


# Load the catch-all configuration
set_profile(_DEFAULT_INI_CONFIG)

# Try to load the user config file
try:
    with open(_DEFAULT_INI_CONFIG_FILENAME) as f:
        logger.info(
            "[*] Loading configuration from '%s'" %
            _DEFAULT_INI_CONFIG_FILENAME)
        set_profile(f.read())
except FileNotFoundError:
    logger.info("[*] File '%s' not available." % _DEFAULT_INI_CONFIG_FILENAME)

# Try to load the user config directory
try:
    for config_file in os.listdir(_DEFAULT_INI_CONFIG_DIR_NAME):
        with open(config_file) as f:
            logger.info("[*] Loading configuration from '%s'" % config_file)
            set_profile(f.read())
except FileNotFoundError:
    logger.info(
        "[*] Directory '%s' not available." %
        _DEFAULT_INI_CONFIG_DIR_NAME)

# ====================== Main ======================

if __name__ == '__main__':
    logger.warning("[-] This module cannot be called directly!")
    pass
