# -*- mode: python ; coding: utf-8 -*-
from os.path import exists
import warnings

import bmicro

NAME = "BMicro"

if not exists("../bmicro/__main__.py"):
    warnings.warn("Cannot find ../bmicro/__main__.py'! " +
                  "Please run pyinstaller from the 'build-recipes' directory.")


a = Analysis(['../bmicro/__main__.py'],
             pathex=['.'],
             hookspath=["."],
             runtime_hooks=None)

options = [ ('u', None, 'OPTION'), ('W ignore', None, 'OPTION') ]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          options,
          exclude_binaries=True,
          name=NAME + ".exe",
          debug=False,
          strip=False,
          upx=False,
          icon=NAME + ".ico",
          console=bool(bmicro.__version__.count("post")),)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=NAME)
