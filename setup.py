"""ShivyC installation script."""

import sys

from setuptools import setup, find_packages
from codecs import open
from os import path

if sys.version_info[0] < 3:
    sys.exit("ShivyC only supports Python 3.")

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='shivyc',
    version='0.1.0',

    description='A C compiler written in Python',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/ShivamSarodia/ShivyC',

    # Author details
    author='Shivam Sarodia',
    author_email='ssarodia@gmail.com',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: C',
        'Topic :: Software Development',
        'Topic :: Software Development :: Compilers',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Build Tools',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
    ],

    keywords='shivyc compiler c programming parsing',
    packages=find_packages(exclude=['tests']),
    install_requires=[],
    package_data={
        'sample': ['include/*.h'],
    },

    entry_points={
        'console_scripts': [
            'shivyc=shivyc.main:main',
        ],
    },
)
