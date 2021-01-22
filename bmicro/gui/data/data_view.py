import pkg_resources

from PyQt5 import QtWidgets, uic

class DataView(QtWidgets.QWidget):
    """
    Class for the data widget
    """

    def __init__(self, *args, **kwargs):

        QtWidgets.QWidget.__init__(self)
        ui_file = pkg_resources.resource_filename('bmicro.gui.data', 'data_view.ui')
        uic.loadUi(ui_file, self)