import pkg_resources

from PyQt5 import QtWidgets, uic

from bmicro.session import Session


class ExtractionView(QtWidgets.QWidget):
    """
    Class for the extraction widget
    """

    def __init__(self, *args, **kwargs):
        super(ExtractionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.extraction', 'extraction_view.ui')
        uic.loadUi(ui_file, self)

        self.update_ui()

    def update_ui(self):
        session = Session.get_instance()
        if not session.selected_repetition:
            # TODO: Clear tab in this case
            return

        calib_keys = session.selected_repetition.calibration.calibration_keys()
        self.combobox_datasets.clear()
        self.combobox_datasets.addItems(calib_keys)
