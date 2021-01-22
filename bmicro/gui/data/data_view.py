import pkg_resources

from PyQt5 import QtWidgets, uic
from bmlab.static_message_b import static_message


class DataView(QtWidgets.QWidget):
    """
    Class for the data widget
    """

    def __init__(self, *args, **kwargs):
        super(DataView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.data', 'data_view.ui')
        uic.loadUi(ui_file, self)

        self.data_test_label.setText(static_message())
