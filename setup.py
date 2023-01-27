from setuptools import setup
import httpimport

# Taken from:
# https://packaging.python.org/en/latest/tutorials/packaging-projects/
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='httpimport',
    version=httpimport.__version__,
    description='Module for remote in-memory Python package/module loading through HTTP',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=httpimport.__author__,
    author_email='john.torakis@gmail.com',
    license='Apache2',
    url=httpimport.__github__,
    py_modules=['httpimport'],
    classifiers=[
        'Development Status :: 6 - Mature',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
    ],
    keywords=[
        'import',
        'loader',
        'memory',
        'http',
        'network'],
)
