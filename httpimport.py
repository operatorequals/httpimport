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

import imp
import sys
import logging

from contextlib import contextmanager
try:
    from urllib2 import urlopen
except:
    from urllib.request import urlopen

__author__ = 'John Torakis - operatorequals'
__version__ = '0.5.2'
__github__ = 'https://github.com/operatorequals/httpimport'

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT)

'''
To enable debug logging set:

	httpimport_logger = logging.getLogger('httpimport')
	httpimport_logger.setLevel(logging.DEBUG)

in your script.
'''
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)
# logger.setLevel(logging.DEBUG)


class HttpImporter(object):
    """
The class that implements the Importer API. Contains the "find_module" and "load_module" methods.
The 'modules' parameter is a list, with the names of the modules/packages that can be imported from the given URL.
The 'base_url' parameter is a string containing the URL where the repository/directory is served through HTTP/S

It is better to not use this class directly, but through its wrappers 'remote_repo' and 'github_repo', that automatically load and unload this class' objects to the 'sys.meta_path' list.
    """

    def __init__(self, modules, base_url):
        self.module_names = modules
        self.base_url = base_url + '/'

    def find_module(self, fullname, path=None):
        logger.debug("FINDER=================")
        logger.debug("[!] Searching %s" % fullname)
        logger.debug("[!] Path is %s" % path)
        logger.info("[@]Checking if in domain >")
        if fullname.split('.')[0] not in self.module_names:
            return None

        logger.info("[@]Checking if built-in >")
        try:
            loader = imp.find_module(fullname, path)
            if loader:
                return None
        except ImportError:
            pass
        logger.info("[@]Checking if it is name repetition >")
        if fullname.split('.').count(fullname.split('.')[-1]) > 1:
            return None

        logger.info("[*]Module/Package '%s' can be loaded!" % fullname)
        return self

    def load_module(self, name):
        imp.acquire_lock()
        logger.debug("LOADER=================")
        logger.debug("[+] Loading %s" % name)
        if name in sys.modules:
            logger.info('[+] Module "%s" already loaded!' % name)
            imp.release_lock()
            return sys.modules[name]

        if name.split('.')[-1] in sys.modules:
            imp.release_lock()
            logger.info('[+] Module "%s" loaded as a top level module!' % name)
            return sys.modules[name.split('.')[-1]]

        module_url = self.base_url + '%s.py' % name.replace('.', '/')
        package_url = self.base_url + '%s/__init__.py' % name.replace('.', '/')
        final_url = None
        final_src = None

        try:
            logger.debug(
                "[+] Trying to import as package from: '%s'" % package_url)
            package_src = urlopen(package_url).read()
            final_src = package_src
            final_url = package_url
        except IOError as e:
            package_src = None
            logger.info("[-] '%s' is not a package:" % name)

        if final_src == None:
            try:
                logger.debug(
                    "[+] Trying to import as module from: '%s'" % module_url)
                module_src = urlopen(module_url).read()
                final_src = module_src
                final_url = module_url
            except IOError as e:
                module_src = None
                logger.info("[-] '%s' is not a module:" % name)
                logger.warning(
                    "[!] '%s' not found in HTTP repository. Moving to next Finder." % name)
                imp.release_lock()
                return None

        logger.debug("[+] Importing '%s'" % name)
        mod = imp.new_module(name)
        mod.__loader__ = self
        mod.__file__ = final_url
        if not package_src:
            mod.__package__ = name
        else:
            mod.__package__ = name.split('.')[0]

        mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1]) + '/']
        logger.debug("[+] Ready to execute '%s' code" % name)
        sys.modules[name] = mod
        exec(final_src, mod.__dict__)
        logger.info("[+] '%s' imported succesfully!" % name)
        imp.release_lock()
        return mod


@contextmanager
# Default 'python -m SimpleHTTPServer' URL
def remote_repo(modules, base_url='http://localhost:8000/'):
    '''
Context Manager that provides remote import functionality through a URL.
The parameters are the same as the HttpImporter class contructor.
    '''
    importer = add_remote_repo(modules, base_url)
    yield
    remove_remote_repo(base_url)


# Default 'python -m SimpleHTTPServer' URL
def add_remote_repo(modules, base_url='http://localhost:8000/'):
    '''
Function that creates and adds to the 'sys.meta_path' an HttpImporter object.
The parameters are the same as the HttpImporter class contructor.
    '''
    if not base_url.startswith('https'):
        logger.warning(
            "[!] Using plain HTTP URLs ('%s') can be a security hazard!" % base_url)
    importer = HttpImporter(modules, base_url)
    sys.meta_path.append(importer)
    return importer


def remove_remote_repo(base_url):
    '''
Function that creates and removes from the 'sys.meta_path' an HttpImporter object given its HTTP/S URL.
    '''
    for importer in sys.meta_path:
        try:
            if importer.base_url[:-1] == base_url:  # an extra '/' is always added
                sys.meta_path.remove(importer)
                return True
        except Exception as e:
            return False


def __create_github_url(username, repo, branch='master'):
    '''
Creates the HTTPS URL that points to the raw contents of a github repository.
    '''
    github_raw_url = 'https://raw.githubusercontent.com/{user}/{repo}/{branch}/'
    return github_raw_url.format(user=username, repo=repo, branch=branch)


def add_github_repo(username=None, repo=None, module=None, branch=None, commit=None):
    '''
Function that creates and adds to the 'sys.meta_path' an HttpImporter object equipped with a Github URL.
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
    url = __create_github_url(username, repo, branch)
    return add_remote_repo([module], url)


@contextmanager
def github_repo(username=None, repo=None, module=None, branch=None, commit=None):
    '''
Context Manager that provides import functionality from Github repositories through HTTPS.
The parameters are the same as the 'add_github_repo' function.
    '''
    importer = add_github_repo(
        username, repo, module=module, branch=branch, commit=commit)
    yield
    url = __create_github_url(username, repo, branch)
    remove_remote_repo(url)


__all__ = [
    'HttpImporter',

    'remote_repo',
    'add_remote_repo',
    'remove_remote_repo',

    'github_repo',
    'add_github_repo',
]
