#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    setup.py
    ~~~~~~~~

    no description available

    :copyright: (c) 2016 by mek.
    :license: see LICENSE for more details.
"""

import codecs
import os
import re
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """Taken from pypa pip setup.py:
    intentionally *not* adding an encoding option to open, See:
       https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    """
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def requirements():
    """Returns requirements.txt as a list usable by setuptools"""
    import os
    reqtxt = os.path.join(here, u'requirements.txt')
    with open(reqtxt) as f:
        return f.read().split()

setup(
    name='niiifty',
    version=find_version("niiifty", "__init__.py"),
    description='A simple IIIF Image API server',
    long_description=read('README.md'),
    classifiers=[
        ],
    author='mek',
    author_email='michael.karpeles@gmail.com',
    url='',
    packages=[
        'niiifty'
        ],
    platforms='any',
    license='LICENSE',
    install_requires=requirements()
)
