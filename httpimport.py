import imp
import sys
import logging

from contextlib import contextmanager
try :
    from urllib2 import urlopen
except :
    from urllib.request import urlopen

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)


class HttpImporter(object):
 
    def __init__(self, modules, base_url):
        self.module_names = modules
        self.base_url = base_url


    def find_module(self, fullname, path=None):
        logger.debug("FINDER=================")
        logger.debug("[!] Searching %s" % fullname)
        logger.debug("[!] Path is %s" % path)
        # if not path :
        logger.info("[@]Checking if in domain >")
        if fullname.split('.')[0] not in self.module_names : return None

        logger.info("[@]Checking if built-in >")
        try :
            loader = imp.find_module( fullname, path )
            if loader : return None
        except ImportError:
            pass
        logger.info("[@]Checking if it is name repetition >")
        # if fullname in sys.modules : return None
        if fullname.split('.').count(fullname.split('.')[-1]) > 1 : return None


        # print "[@]Checking if already loaded >"
        # # if fullname in sys.modules : return None
        # if fullname.split('.')[-1] in sys.modules and path : return None


        logger.info("[*]Module/Package '%s' can be loaded!" % fullname)
        return self
 

    def load_module(self, name):
        imp.acquire_lock()
        logger.debug("LOADER=================")

        logger.debug( "[+] Loading %s" % name )
        # logger.debug( '[>] ' + '\n[>] '.join(x for x in sys.modules.keys() if x.startswith('covert')) )
        if name in sys.modules:
            logger.info( '[+] Module "%s" already loaded!' % name )
            imp.release_lock()
            return sys.modules[name]

        # if name.split('.')[-1] in sys.modules:
        #     print '[+] Module "%s" already loaded!' % name.split('.')[-1]
        #     # return sys.modules[name]
        #     return None


        if name.split('.')[-1] in sys.modules:
            imp.release_lock()
            logger.info('[+] Module "%s" loaded as a top level module!' % name)
            return sys.modules[name.split('.')[-1]]


        module_url = self.base_url + '%s.py'  % name.replace('.','/')
        package_url = self.base_url + '%s/__init__.py'  % name.replace('.','/')
        final_url = None
        final_src = None


        try :
            logger.debug("[+] Trying to import as package from: '%s'" % package_url)
            package_src = urlopen(package_url).read()
            final_src = package_src
            final_url = package_url
        except IOError as e:
            package_src = None
            logger.info( "[-] '%s' is not a package:" % name )
            # print e
            # raise ImportError("Cannot import %s" % name)

        if final_src == None :
            try :
                logger.debug("[+] Trying to import as module from: '%s'" % module_url)
                module_src = urlopen(module_url).read()
                final_src = module_src
                final_url = module_url
            except IOError as e:
                module_src = None
                logger.info( "[-] '%s' is not a module:" % name )
                logger.warn( "[!] '%s' not found in HTTP repository. Moving to next Finder." % name )
                imp.release_lock()
                return None
                # raise ImportError("Cannot import %s" % name)

        logger.debug("[+] Importing '%s'" % name)
        mod = imp.new_module(name)
        mod.__loader__ = self
        mod.__file__ = final_url
        if not package_src :
            mod.__package__ = name
        else :
            mod.__package__ = name.split('.')[0]

        mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1])+'/']
        logger.debug( "[+] Ready to execute '%s' code" % name )
        sys.modules[name] = mod
        # try :
        #     exec final_src in mod.__dict__
        # except :
        exec(final_src, mod.__dict__)    
        logger.info("[+] '%s' imported succesfully!" % name)
        # pprint(mod.__dict__)
        # print [print "%s - %s" % (k,v) for k,v in mod.items()]

        # if '.' not in name :
        # else :
        #     pass
        imp.release_lock()
        return mod
        # raise ImportError("%s is blocked and cannot be imported" % name)
 


@contextmanager
def remote_import( modules, base_url = 'http://localhost:8000/' ):
    importer = addRemoteRepo( modules, base_url )
    yield
    removeRemoteRepo(base_url)


def addRemoteRepo( modules, base_url = 'http://localhost:8000/' ) :
    importer = HttpImporter( modules, base_url )
    sys.meta_path.append( importer )
    return importer

def removeRemoteRepo( base_url ) :
    for importer in sys.meta_path :
        try :
            if importer.base_url == base_url :
                sys.meta_path.remove( importer )
                return True
        except Exception as e :
                return False