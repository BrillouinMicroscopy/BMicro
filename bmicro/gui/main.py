import pathlib
import pkg_resources

from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from bmlab.session import Session

from . import data
from . import extraction
from . import calibration
from . import peak_selection
from . import evaluation

from bmicro import __version__ as bmicroversion
from bmlab import __version__ as bmlabversion


def check_event_mime_data(event):
    """ Returns the path to local file if h5 file """
    if event.mimeData().hasUrls():
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.endswith(".h5"):
                return path
    return False


class BMicro(QtWidgets.QMainWindow):
    """
    Class for the main window of BMicro.
    The application can be started from console by running

        python -m bmicro

    """

    def __init__(self, *args, **kwargs):
        # Settings are stored in the .ini file format. Even though
        # `self.settings` may return integer/bool in the same session,
        # in the next session, it will reliably return strings. Lists
        # of strings (comma-separated) work nicely though.
        QtCore.QCoreApplication.setOrganizationName("BMicro")
        QtCore.QCoreApplication.setOrganizationDomain(
            "bmicro.readthedocs.io")
        QtCore.QCoreApplication.setApplicationName("BMicro")
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.Format.IniFormat)
        # Some promoted widgets may need the above constants set in order
        # to access the settings upon initialization.

        """ Initializes BMicro."""
        super(BMicro, self).__init__(*args, **kwargs)
        ui_file = pkg_resources.resource_filename('bmicro.gui', 'main.ui')
        uic.loadUi(ui_file, self)
        QtCore.QCoreApplication.setApplicationName('BMicro')

        self.tabWidget.currentChanged.connect(self.update_ui)
        self.build_tabs()

        self.connect_menu()

        self.connect_drag_drop()

        self.setAcceptDrops(True)

        self.reset_ui()

        self.settings = QtCore.QSettings()

    def build_tabs(self):
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

    def connect_drag_drop(self):
        self.dragEnterEvent = self.drag_enter_event
        self.dropEvent = self.drop_event

    def connect_menu(self):
        """ Registers the menu actions """
        self.action_open.triggered.connect(self.open_file)
        self.action_close.triggered.connect(self.close_file)
        self.action_save.triggered.connect(self.save_session)
        self.action_exit.triggered.connect(self.exit_app)

        self.action_about.triggered.connect(self.on_action_about)

    def open_file(self, file_name=None):
        """ Show open file dialog and load file. """
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(
                self, 'Open File...',
                directory=self.settings.value("path/last-used"),
                filter='*.h5')

        """ file_name is empty if user selects 'Cancel' in FileDialog """
        if not file_name:
            return
        else:
            self.settings.setValue("path/last-used",
                                   str(pathlib.Path(file_name).parent))

        session = Session.get_instance()
        try:
            session.set_file(file_name)
        except Exception:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText('Unable to load file:')
            msg.setInformativeText(str(file_name))
            msg.setWindowTitle('Invalid File Error')
            msg.exec()

        self.update_ui()

    def close_file(self):
        Session.get_instance().clear()
        self.reset_ui()

    def reset_ui(self):
        """
        Resets the UI if a file is closed.
        """
        self.widget_data_view.reset_ui()
        self.widget_extraction_view.reset_ui()
        self.widget_calibration_view.reset_ui()
        self.widget_peak_selection_view.reset_ui()
        self.widget_evaluation_view.reset_ui()

    def update_ui(self, new_tab_index=-1):
        # If no tab index is specified, we update all tabs
        # (e.g. when a new file is opened).
        # Otherwise, we only update the newly selected tab.
        if new_tab_index == -1:
            self.widget_data_view.update_ui()
            self.widget_extraction_view.update_ui()
            self.widget_calibration_view.update_ui()
            self.widget_peak_selection_view.update_ui()
            self.widget_evaluation_view.update_ui()
        elif new_tab_index == 0:
            self.widget_data_view.update_ui()
        elif new_tab_index == 1:
            self.widget_extraction_view.update_ui()
        elif new_tab_index == 2:
            self.widget_calibration_view.update_ui()
        elif new_tab_index == 3:
            self.widget_peak_selection_view.update_ui()
        elif new_tab_index == 4:
            self.widget_evaluation_view.update_ui()

    def drag_enter_event(self, event):
        """ Handles dragging a file over the GUI """
        if check_event_mime_data(event):
            event.accept()
        else:
            event.ignore()

    def drop_event(self, event):
        """ Handles dropping a file, opens if h5"""
        path = check_event_mime_data(event)
        if path:
            self.open_file(path)

    def save_session(self):
        """ Save the session data to file with ending '.bms' """
        Session.get_instance().save()

    def exit_app(self):
        QtCore.QCoreApplication.quit()

    def on_action_about(self):
        gh = "BrillouinMicroscopy/BMicro"
        rtd = "bmicro.readthedocs.io"
        about_text = "BMicro is a graphical user interface " \
            + "for the analysis of Brillouin microscopy data.<br><br>" \
            + f"Using bmlab {bmlabversion}<br><br>" \
            + "Author: Raimund Schlüßler and others<br>" \
            + "GitHub: " \
            + "<a href='https://github.com/{gh}'>{gh}</a><br>".format(gh=gh) \
            + "Documentation: " \
            + "<a href='https://{rtd}'>{rtd}</a><br>".format(rtd=rtd)
        QtWidgets.QMessageBox.about(self,
                                    f"BMicro {bmicroversion}", about_text)
