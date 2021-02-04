import pkg_resources
import sys

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from ..session import Session
from .._version import version as __version__

from . import data
from . import extraction
from . import calibration
from . import peak_selection
from . import evaluation


class BMicro(QtWidgets.QMainWindow):
    """
    Class for the main window of BMicro.
    The application can be started from console by running

        python -m bmicro

    """

    def __init__(self, *args, **kwargs):
        """ Initializes BMicro."""
        super(BMicro, self).__init__(*args, **kwargs)
        ui_file = pkg_resources.resource_filename('bmicro.gui', 'main.ui')
        uic.loadUi(ui_file, self)
        QtCore.QCoreApplication.setApplicationName('BMicro')

        self.widget_data_view = data.DataView(self)
        self.layout_data = QtWidgets.QVBoxLayout()
        self.tab_data.setLayout(self.layout_data)
        self.layout_data.addWidget(self.widget_data_view)

        self.widget_extraction_view = extraction.ExtractionView(self)
        self.layout_extraction = QtWidgets.QVBoxLayout()
        self.tab_extraction.setLayout(self.layout_extraction)
        self.layout_extraction.addWidget(self.widget_extraction_view)

        self.widget_calibration_view = calibration.CalibrationView(self)
        self.layout_calibration = QtWidgets.QVBoxLayout()
        self.tab_calibration.setLayout(self.layout_calibration)
        self.layout_calibration.addWidget(self.widget_calibration_view)

        self.widget_peak_selection_view = peak_selection.PeakSelectionView(
            self)
        self.layout_peak_selection = QtWidgets.QVBoxLayout()
        self.tab_peak_selection.setLayout(self.layout_peak_selection)
        self.layout_peak_selection.addWidget(self.widget_peak_selection_view)

        self.widget_evaluation_view = evaluation.EvaluationView(self)
        self.layout_evaluation = QtWidgets.QVBoxLayout()
        self.tab_evaluation.setLayout(self.layout_evaluation)
        self.layout_evaluation.addWidget(self.widget_evaluation_view)

        self.connect_menu()

        self.session = Session.get_instance()

        # if "--version" was specified, print the version and exit
        if "--version" in sys.argv:
            print(__version__)
            QtWidgets.QApplication.processEvents()
            sys.exit(0)

    def connect_menu(self):
        """ Registers the menu actions """
        self.action_open.triggered.connect(self.open_file)

    def open_file(self, file_name=None):
        """ Show open file dialog and load file. """
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(self, 'Open File...',
                                                   filter='*.h5')
        try:
            self.session.set_file(file_name)
        except Exception:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText('Unable to load file:')
            msg.setInformativeText(str(file_name))
            msg.setWindowTitle('Invalid File Error')
            msg.exec_()
            self.session.clear()

        self.update_ui()

    def update_ui(self):
        self.widget_data_view.update_ui()
