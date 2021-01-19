import sys

from PyQt5 import QtWidgets

from .gui import BMicro


def main():
    """
    Starts the BMicro application and handles its life cycle.
    """
    app = QtWidgets.QApplication(sys.argv)
    main = BMicro()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
