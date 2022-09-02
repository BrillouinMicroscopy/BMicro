#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os.path import exists, dirname, realpath
from setuptools import setup, find_packages
import sys

author = u"BMicro developers"
# authors in alphabetical order
authors = [
    "Matthias Bär",
    "Paul Müller",
    "Raimund Schlüßler",
    "Timon Beck",
]
description = 'GUI for Brillouin evaluation'
name = 'bmicro'
year = "2022"


sys.path.insert(0, realpath(dirname(__file__))+"/"+name)
try:
    from _version import version
except BaseException:
    version = "unknown"


setup(
    name=name,
    author=author,
    author_email='dev@craban.de',
    url='https://github.com/BrillouinMicroscopy/BMicro',
    version=version,
    packages=find_packages(),
    package_dir={name: name},
    include_package_data=True,
    license="GPL v3",
    description=description,
    long_description=open('README.rst').read() if exists('README.rst') else '',
    install_requires=["bmlab>=0.5.1",
                      "h5py>=2.10.0",
                      "matplotlib",
                      "numpy>=1.17.0",
                      "pyqt6>=6.2.3, <6.3.0",
                      "pyqt6-qt6>=6.2.3, <6.3.0",
                      "pytest",
                      "pytest-qt",
                      "pytest_mock",
                      "scikit-image",
                      "scipy<=1.9.0"
                      ],
    python_requires=">=3.7",
    keywords=["Brillouin Microscopy"],
    classifiers=['Operating System :: OS Independent',
                 'Programming Language :: Python :: 3',
                 'Topic :: Scientific/Engineering :: Visualization',
                 'Intended Audience :: Science/Research',
                 ],
    platforms=['ALL'],
)
