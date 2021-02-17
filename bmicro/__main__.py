import os
import pkg_resources
import sys

from PyQt5 import QtGui, QtWidgets

from bmicro.gui.main import BMicro

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

    main = BMicro()
    main.show()

    if len(sys.argv) > 1:
        file_to_load = sys.argv[1]
        main.open_file(file_to_load)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
