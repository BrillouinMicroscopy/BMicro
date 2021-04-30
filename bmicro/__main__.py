import os
import pkg_resources
import sys
import logging

from PyQt5 import QtCore, QtGui, QtWidgets

from bmicro.gui.main import BMicro
from bmicro._version import version as __version__

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:  # noqa E722
    pass


def main():
    """
    Starts the BMicro application and handles its life cycle.
    """
    app = QtWidgets.QApplication(sys.argv)
    # set window icon
    imdir = pkg_resources.resource_filename("bmicro", "img")
    icon_path = os.path.join(imdir, "icon.png")
    app.setWindowIcon(QtGui.QIcon(icon_path))

    mw = BMicro()
    mw.show()

    # set log level
    for arg in sys.argv:
        if arg.startswith('--log='):
            log_level = arg[6:]
            logging.basicConfig(level=log_level)
            break

    # load dataset
    if sys.argv[-1].endswith('.h5'):
        mw.open_file(sys.argv[-1])

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
