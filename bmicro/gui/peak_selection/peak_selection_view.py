import pkg_resources

from PyQt5 import QtWidgets, uic


class PeakSelectionView(QtWidgets.QWidget):
    """
    Class for the peak selection widget
    """

    def __init__(self, *args, **kwargs):
        super(PeakSelectionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.peak_selection', 'peak_selection_view.ui')
        uic.loadUi(ui_file, self)
