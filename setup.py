from setuptools import setup


import httpimport


# Get the long description from the README file
# And also convert to reST
# MD to RST Convert Line acquired from:
# https://bons.ai/blog/markdown-for-pypi ->
# https://github.com/BonsaiAI/bonsai-config/blob/0.3.1/setup.py#L9
try:
	from pypandoc import convert

	def read_md(f): return convert(f, 'rst').replace("~",'^')

except ImportError:
	print("warning: pypandoc module not found, could not convert Markdown to RST")
	def read_md(f): return open(f, 'r').read()


setup(name='httpimport',
	  version=httpimport.__version__,
	  description='Module for remote in-memory Python package/module loading through HTTP',
	  long_description=read_md('README.md'),
	  author=httpimport.__author__,
	  author_email='john.torakis@gmail.com',
	  license='Apache2',
	  url=httpimport.__github__,
	  py_modules=['httpimport'],
	  classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
 		'Intended Audience :: Developers',
	 	  ],
  	  keywords = 'import, loader, memory, http',
	  )
