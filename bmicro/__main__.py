import os
import pkg_resources
import sys

from PyQt5 import QtGui, QtWidgets

from .gui.main import BMicro


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
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
