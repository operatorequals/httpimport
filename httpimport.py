'''
Copyright 2017 John Torakis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import types
import sys
import logging
import io
import zipfile
import tarfile
import os

from contextlib import contextmanager
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

__author__ = 'John Torakis - operatorequals'
__version__ = '0.7.2'
__github__ = 'https://github.com/operatorequals/httpimport'


'''
To enable debug logging set:

>>> import logging; logging.getLogger('httpimport').setLevel(logging.DEBUG)

in your script.
'''

log_level = logging.WARN
log_format = '%(message)s'

logger = logging.getLogger(__name__)
logger.setLevel(log_level)
log_handler = logging.StreamHandler()
log_handler.setLevel(log_level)
log_formatter = logging.Formatter(log_format)
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

NON_SOURCE = False
INSECURE = False
RELOAD = False
LEGACY = (sys.version_info.major == 2)

if LEGACY:
    logger.warning("[!] LEGACY flag automatically enabled for Python 2.")
    import imp
    logger.warning("[!] Using imp (deprecated) instead of importlib.")
else:
    import importlib



class HttpImporter(object):
    """
The class that implements the Importer API. Contains the "find_module" and "load_module" methods.
The 'modules' parameter is a list, with the names of the modules/packages that can be imported from the given URL.
The 'base_url' parameter is a string containing the URL where the repository/directory is served through HTTP/S

It is better to not use this class directly, but through its wrappers ('remote_repo', 'github_repo', etc) that automatically load and unload this class' objects to the 'sys.meta_path' list.
    """

    TAR_ARCHIVE = 'tar'
    ZIP_ARCHIVE = 'zip'
    WEB_ARCHIVE = 'html'
    ARCHIVE_TYPES = [
        ZIP_ARCHIVE,
        TAR_ARCHIVE,
        WEB_ARCHIVE
    ]

    def __init__(self, modules, base_url, zip_pwd=None):

        self.module_names = modules
        self.base_url = base_url + '/'
        self.non_source = NON_SOURCE
        self.in_progress = {}
        self.__zip_pwd = zip_pwd

        if not INSECURE and not self.__isHTTPS(base_url) :
            logger.warning("[-] '%s.INSECURE' is not set! Aborting..." % (__name__))
            raise Exception("Plain HTTP URL provided with '%s.INSECURE' not set" % __name__)

        if not self.__isHTTPS(base_url):
            logger.warning("[!] Using non HTTPS URLs ('%s') can be a security hazard!" % self.base_url)

        try:
            self.filetype, self.archive = _detect_filetype(base_url)
            logger.info("[+] Filetype detected '%s' for '%s'" % (self.filetype, self.base_url))
        except IOError:
            raise ImportError("URL content cannot be detected or opened (%s)" % self.base_url)

        self.is_archive = False
        if self.filetype in [HttpImporter.TAR_ARCHIVE, HttpImporter.ZIP_ARCHIVE]:
            self.is_archive = True

        if self.is_archive:
            logger.info("[+] Archive file loaded successfully from '%s'!" % self.base_url)
            self._paths = _list_archive(self.archive)
            # # "/".join(x.filename.split('/')[traverse_dir:])

    def _mod_to_paths(self, fullname):
        # get the python module name
        py_filename = fullname.replace(".", os.sep) + ".py"
        # get the filename if it is a package/subpackage
        py_package = fullname.replace(".", os.sep, fullname.count(".") - 1) + "/__init__.py"
        if py_filename in self._paths:
            return py_filename
        elif py_package in self._paths:
            return py_package
        else:
            return None


    def find_module(self, fullname, path=None):
        logger.debug("FINDER=================")
        logger.debug("[!] Searching %s" % fullname)
        logger.debug("[!] Path is %s" % path)
        logger.info("[@] Checking if in declared remote module names >")
        if fullname.split('.')[0] not in self.module_names:
            logger.info("[-] Not found!")
            return None

        if fullname in self.in_progress:
            return None

        self.in_progress[fullname] = True

        logger.info("[@] Checking if built-in >")
        try:
            if LEGACY:
                loader = imp.find_module(fullname, path)
            else:
                try:    # After Python3.5
                    loader = importlib.util.find_spec(fullname, path)
                except AttributeError:
                    loader = importlib.find_loader(fullname, path)
            if loader:
                logger.info("[-] Found locally!")
                return None
        except ImportError:
            pass
        logger.info("[@] Checking if it is name repetition >")
        if fullname.split('.').count(fullname.split('.')[-1]) > 1:
            logger.info("[-] Found locally!")
            return None

        if self.is_archive:
            logger.info("[@] Checking if module exists in loaded Archive file >")
            if self._mod_to_paths(fullname) is  None:
                logger.info("[-] Not Found in Archive file!")
                return None

        logger.info("[*]Module/Package '%s' can be loaded!" % fullname)
        del(self.in_progress[fullname])
        return self


    def load_module(self, name):
        if LEGACY: imp.acquire_lock()
        logger.debug("LOADER=================")
        logger.debug("[+] Loading %s" % name)
        if name in sys.modules and not RELOAD:
            logger.info('[+] Module "%s" already loaded!' % name)
            if LEGACY: imp.release_lock()
            return sys.modules[name]

        if name.split('.')[-1] in sys.modules and not RELOAD:
            logger.info('[+] Module "%s" loaded as a top level module!' % name)
            if LEGACY: imp.release_lock()
            return sys.modules[name.split('.')[-1]]

        if self.is_archive:
            zip_name = self._mod_to_paths(name)
            if not zip_name in self._paths:
                logger.info('[-] Requested module/package "%s" name not available in Archive file list!' % zip_name)
                if LEGACY: imp.release_lock()
                raise ImportError(zip_name)

        module_url = self.base_url + '%s.py' % name.replace('.', '/')
        package_url = self.base_url + '%s/__init__.py' % name.replace('.', '/')
        final_url = None
        final_src = None

        if self.is_archive:
            package_src = _open_archive_file(self.archive, zip_name, 'r', zip_pwd=self.__zip_pwd).read()
            logger.info('[+] Source from zipped file "%s" loaded!' % zip_name)       
            final_src = package_src

        else:
            try:
                logger.debug("[+] Trying to import as package from: '%s'" % package_url)
                package_src = None
                if self.non_source :    # Try the .pyc file
                    package_src = self.__fetch_compiled(package_url)
                if package_src == None :
                    package_src = urlopen(package_url).read()
                final_src = package_src
                final_url = package_url
            except IOError as e:
                package_src = None
                logger.info("[-] '%s' is not a package:" % name)

            if final_src == None:
                try:
                    logger.debug("[+] Trying to import as module from: '%s'" % module_url)
                    module_src = None
                    if self.non_source :    # Try the .pyc file
                        module_src = self.__fetch_compiled(module_url)
                    if module_src == None : # .pyc file not found, falling back to .py
                        module_src = urlopen(module_url).read()
                    final_src = module_src
                    final_url = module_url
                except IOError as e:
                    module_src = None
                    logger.info("[-] '%s' is not a module:" % name)
                    logger.warning("[!] '%s' not found in HTTP repository. Moving to next Finder." % name)
                    if LEGACY: imp.release_lock()
                    return None

        logger.debug("[+] Importing '%s'" % name)
        if LEGACY:
            mod = imp.new_module(name)
        else:
            mod = types.ModuleType(name)
        mod.__loader__ = self
        mod.__file__ = final_url
        if not package_src:
            mod.__package__ = name
        else:
            mod.__package__ = name.split('.')[0]

        try:
            mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1]) + '/']
        except:
            mod.__path__ = self.base_url
        logger.debug("[+] Ready to execute '%s' code" % name)
        sys.modules[name] = mod
        exec(final_src, mod.__dict__)
        logger.info("[+] '%s' imported succesfully!" % name)
        if LEGACY: imp.release_lock()
        return mod

    def __fetch_compiled(self, url) :
        import marshal
        module_src = None
        try :
            module_compiled = urlopen(url + 'c').read()  # from blah.py --> blah.pyc
            try :
                module_src = marshal.loads(module_compiled[8:]) # Strip the .pyc file header of Python up to 3.3
                return module_src
            except ValueError :
                pass
            try :
                module_src = marshal.loads(module_compiled[12:])# Strip the .pyc file header of Python 3.3 and onwards (changed .pyc spec)
                return module_src
            except ValueError :
                pass
        except IOError as e:
            logger.debug("[-] No compiled version ('.pyc') for '%s' module found!" % url.split('/')[-1])
        return module_src


    def __isHTTPS(self, url) :
        return self.base_url.startswith('https') 

def _open_archive_file(archive_obj, filepath, mode='r', zip_pwd=None):
    if isinstance(archive_obj, tarfile.TarFile):
        return archive_obj.extractfile(filepath)
    if isinstance(archive_obj, zipfile.ZipFile):
        return archive_obj.open(filepath, mode, pwd=zip_pwd)

    raise ValueError("Object is not a ZIP or TAR archive")

def _list_archive(archive_obj):
    if isinstance(archive_obj, tarfile.TarFile):
        return archive_obj.getnames()
    if isinstance(archive_obj, zipfile.ZipFile):
        return [x.filename for x in archive_obj.filelist]

    raise ValueError("Object is not a ZIP or TAR archive")

def _detect_filetype(base_url):
    try:
        resp_obj = urlopen(base_url);
        resp = resp_obj.read()
        if "text" in resp_obj.headers['Content-Type']:
            logger.info("[+] Response of '%s' is HTML. - Content-Type: %s" % (base_url, resp_obj.headers['Content-Type']))
            return HttpImporter.WEB_ARCHIVE, resp

    except Exception as e:   # Base URL is not callable in GitHub /raw/ contents - returns 400 Error
        logger.info("[!] Response of '%s' triggered '%s'" % (base_url, e))
        return HttpImporter.WEB_ARCHIVE, None

    resp_io = io.BytesIO(resp)
    try:
        tar = tarfile.open(fileobj=resp_io, mode='r:*')
        logger.info("[+] Response of '%s' is a Tarball" % base_url)
        return HttpImporter.TAR_ARCHIVE, tar
    except tarfile.ReadError:
        logger.info("Response of '%s' is not a (compressed) tarball" % base_url)

    try:
        zip = zipfile.ZipFile(resp_io)
        logger.info("[+] Response of '%s' is a ZIP file" % base_url)
        return HttpImporter.ZIP_ARCHIVE, zip
    except zipfile.BadZipfile:
        logger.info("Response of '%s' is not a ZIP file" % base_url)

    raise IOError("URL content is Invalid")

@contextmanager
# Default 'python -m SimpleHTTPServer' URL
def remote_repo(modules, base_url='http://localhost:8000/', zip_pwd=None):
    '''
Context Manager that provides remote import functionality through a URL.
The parameters are the same as the HttpImporter class contructor.
    '''
    importer = add_remote_repo(modules, base_url, zip_pwd=zip_pwd)
    try:
        yield
    except ImportError as e:
        raise e
    finally:    # Always remove the added HttpImporter from sys.meta_path 
        remove_remote_repo(base_url)


# Default 'python -m SimpleHTTPServer' URL
def add_remote_repo(modules, base_url='http://localhost:8000/', zip_pwd=None):
    '''
Function that creates and adds to the 'sys.meta_path' an HttpImporter object.
The parameters are the same as the HttpImporter class contructor.
    '''
    importer = HttpImporter(modules, base_url, zip_pwd=zip_pwd)
    sys.meta_path.insert(0, importer)
    return importer


def remove_remote_repo(base_url):
    '''
Function that removes from the 'sys.meta_path' an HttpImporter object given its HTTP/S URL.
    '''
    for importer in sys.meta_path:
        try:
            if importer.base_url.startswith(base_url):  # an extra '/' is always added
                sys.meta_path.remove(importer)
                return True
        except AttributeError as e:
            pass
    return False


def __create_github_url(username, repo, branch='master'):
    '''
Creates the HTTPS URL that points to the raw contents of a github repository.
    '''
    github_raw_url = 'https://raw.githubusercontent.com/{user}/{repo}/{branch}/'
    return github_raw_url.format(user=username, repo=repo, branch=branch)


def __create_bitbucket_url(username, repo, branch='master'):
    '''
Creates the HTTPS URL that points to the raw contents of a bitbucket repository.
    '''
    bitbucket_raw_url = 'https://bitbucket.org/{user}/{repo}/raw/{branch}/'
    return bitbucket_raw_url.format(user=username, repo=repo, branch=branch)

def __create_gitlab_url(username, repo, branch='master', domain='gitlab.com'):
    '''
Creates the HTTPS URL that points to the raw contents of a gitlab repository.
    '''

    '''
    Gitlab returns a 308 response code for redirects,
    so the URLs have to be exact, as urllib recognises 308 as error.
    '''
    gitlab_raw_url = 'https://{domain}/{user}/{repo}/raw/{branch}'
    return gitlab_raw_url.format(user=username, repo=repo, branch=branch, domain=domain)



def _add_git_repo(url_builder, username=None, repo=None, module=None, branch=None, commit=None, **kw):
    '''
Function that creates and adds to the 'sys.meta_path' an HttpImporter object equipped with a URL of a Online Git server.
The 'url_builder' parameter is a function that accepts the username, repo and branch/commit, and creates a HTTP/S URL of a Git server. Compatible functions are '__create_github_url', '__create_bitbucket_url'.
The 'username' parameter defines the Github username which is the repository's owner.
The 'repo' parameter defines the name of the repo that contains the modules/packages to be imported.
The 'module' parameter is optional and is a list containing the modules/packages that are available in the chosen Github repository.
If it is not provided, it defaults to the repositories name, as it is common that the a Python repository at "github.com/someuser/somereponame" contains a module/package of "somereponame".
The 'branch' and 'commit' parameters cannot be both populated at the same call. They specify the branch (last commit) or specific commit, that should be served.
    '''
    if username == None or repo == None:
        raise Error("'username' and 'repo' parameters cannot be None")
    if commit and branch:
        raise Error("'branch' and 'commit' parameters cannot be both set!")

    if commit:
        branch = commit
    if not branch:
        branch = 'master'
    if not module:
        module = repo
    if type(module) == str:
        module = [module]
    url = url_builder(username, repo, branch, **kw)
    return add_remote_repo(module, url)


@contextmanager
def github_repo(username=None, repo=None, module=None, branch=None, commit=None):
    '''
Context Manager that provides import functionality from Github repositories through HTTPS.
The parameters are the same as the '_add_git_repo' function. No 'url_builder' function is needed.
    '''
    importer = _add_git_repo(__create_github_url,
        username, repo, module=module, branch=branch, commit=commit)
    try:
        yield
    except ImportError as e:
        raise e
    finally:    # Always remove the added HttpImporter from sys.meta_path 
        remove_remote_repo(importer.base_url)



@contextmanager
def bitbucket_repo(username=None, repo=None, module=None, branch=None, commit=None):
    '''
Context Manager that provides import functionality from BitBucket repositories through HTTPS.
The parameters are the same as the '_add_git_repo' function. No 'url_builder' function is needed.
    '''
    importer = _add_git_repo(__create_bitbucket_url,
        username, repo, module=module, branch=branch, commit=commit)
    try:
        yield
    except ImportError as e:
        raise e
    finally:    # Always remove the added HttpImporter from sys.meta_path 
        remove_remote_repo(importer.base_url)



@contextmanager
def gitlab_repo(username=None, repo=None, module=None, branch=None, commit=None, domain='gitlab.com'):
    '''
Context Manager that provides import functionality from Github repositories through HTTPS.
The parameters are the same as the '_add_git_repo' function. No 'url_builder' function is needed.
    '''
    importer = _add_git_repo(__create_gitlab_url,
        username, repo, module=module, branch=branch, commit=commit, domain=domain)
    try:
        yield
    except ImportError as e:    
        raise e
    finally:    # Always remove the added HttpImporter from sys.meta_path 
        remove_remote_repo(importer.base_url)


def load(module_name, url = 'http://localhost:8000/', zip_pwd=None):
    '''
Loads a module on demand and returns it as a module object. Does NOT load it to the Namespace.
Example:

>>> mod = httpimport.load('covertutils','http://localhost:8000/')
>>> mod
<module 'covertutils' from 'http://localhost:8000//covertutils/__init__.py'>
>>> 
    '''
    importer = HttpImporter([module_name], url, zip_pwd=zip_pwd)
    loader = importer.find_module(module_name)
    if loader != None :
        module = loader.load_module(module_name)
        if module :
            return module
    raise ImportError("Module '%s' cannot be imported from URL: '%s'" % (module_name, url) )



__all__ = [
    'HttpImporter',

    'add_remote_repo',
    'remove_remote_repo',

    'remote_repo',
    'github_repo',
    'bitbucket_repo',
    'gitlab_repo'
]
