import pkg_resources

from PyQt5 import QtWidgets, uic

class ExtractionView(QtWidgets.QWidget):
    """
    Class for the extraction widget
    """

    def __init__(self, *args, **kwargs):
        super(ExtractionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename('bmicro.gui.extraction', 'extraction_view.ui')
        uic.loadUi(ui_file, self)