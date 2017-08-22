import imp
import sys
from pprint import pprint
from contextlib import contextmanager

try :
    from urllib.request import urlopen
except :
    from urllib2 import urlopen


class HttpImporter(object):
 
    def __init__(self, modules, base_url):
        self.module_names = modules
        self.base_url = base_url


    def find_module(self, fullname, path=None):
        print "FINDER================="
        print "[!] Searching %s" % fullname
        print "[!] Path is %s" % path
        print fullname.split('.')
        # if not path :
        print "[@]Checking if in domain >"
        if fullname.split('.')[0] not in self.module_names : return None


        print "[@]Checking if built-in >"        
        try :
            loader = imp.find_module( fullname, path )
            # print loader[0]
            if loader : return None
        except ImportError:
            pass
        print "[@]Checking if it is name repetition >"
        # if fullname in sys.modules : return None
        if fullname.split('.').count(fullname.split('.')[-1]) > 1 : return None


        # print "[@]Checking if already loaded >"
        # # if fullname in sys.modules : return None
        # if fullname.split('.')[-1] in sys.modules and path : return None


        print "[*] Sent to Loader!"
        return self
 

    def load_module(self, name):
        imp.acquire_lock()
        print "LOADER================="

        print "[+] Loading %s" % name
        print "[+] "+name
        print '\n[>] '.join(x for x in sys.modules.keys() if x.startswith('covert'))
        if name in sys.modules:
            print '[+] Module "%s" already loaded!' % name
            imp.release_lock()
            return sys.modules[name]

        # if name.split('.')[-1] in sys.modules:
        #     print '[+] Module "%s" already loaded!' % name.split('.')[-1]
        #     # return sys.modules[name]
        #     return None


        if name.split('.')[-1] in sys.modules:
            imp.release_lock()
            return sys.modules[name.split('.')[-1]]


        module_url = self.base_url + '%s.py'  % name.replace('.','/')
        package_url = self.base_url + '%s/__init__.py'  % name.replace('.','/')
        final_url = None
        final_src = None


        try :
            package_src = urlopen(package_url).read()
            final_src = package_src
            final_url = package_url
        except IOError as e:
            package_src = None
            print "[-] %s is not a package:" % name
            # print e
            # raise ImportError("Cannot import %s" % name)

        if final_src == None :
            try :
                module_src = urlopen(module_url).read()
                final_src = module_src
                final_url = module_url
            except IOError as e:
                module_src = None
                print "[-] %s is not a module:" % name
                # print e
                imp.release_lock()
                return None
                # raise ImportError("Cannot import %s" % name)



        mod = imp.new_module(name)
        mod.__loader__ = self
        mod.__file__ = final_url
        if not package_src :
            mod.__package__ = name
        else :
            mod.__package__ = name.split('.')[0]

        mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1])+'/']
        print "[+] Ready to populate %s" % name
        sys.modules[name] = mod
        exec final_src in mod.__dict__
        print "[*] Populated %s !" % name
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
                print e
                return False