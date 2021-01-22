import pkg_resources

from PyQt5 import QtWidgets, uic

class CalibrationView(QtWidgets.QWidget):
    """
    Class for the calibration widget
    """

    def __init__(self, *args, **kwargs):
        super(CalibrationView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename('bmicro.gui.calibration', 'calibration_view.ui')
        uic.loadUi(ui_file, self)