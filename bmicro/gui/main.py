import pkg_resources
import sys

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

# from bmlab.session import Session

from .._version import version


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
        """ Initializes BMicro."""
        super(BMicro, self).__init__(*args, **kwargs)
        ui_file = pkg_resources.resource_filename('bmicro.gui', 'main.ui')
        uic.loadUi(ui_file, self)
        QtCore.QCoreApplication.setApplicationName('BMicro')

        # print version and exit
        if "--version" in sys.argv:
            print(version)
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents,
                                                 1000)
            sys.exit(0)

        self.tabWidget.currentChanged.connect(self.update_ui)
        self.build_tabs()

        self.connect_menu()

        self.connect_drag_drop()

        self.setAcceptDrops(True)

    def connect_drag_drop(self):
        self.dragEnterEvent = self.drag_enter_event
        self.dropEvent = self.drop_event

    def connect_menu(self):
        """ Registers the menu actions """
        self.action_open.triggered.connect(self.open_file)
        self.action_close.triggered.connect(self.close_file)
        self.action_save.triggered.connect(self.save_session)

    def open_file(self, file_name=None):
        """ Show open file dialog and load file. """
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(self, 'Open File...',
                                                       filter='*.h5')

        """ file_name is empty if user selects 'Cancel' in FileDialog """
        if not file_name:
            return

        # session = Session.get_instance()
        try:
            pass
            # session.set_file(file_name)
        except Exception:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText('Unable to load file:')
            msg.setInformativeText(str(file_name))
            msg.setWindowTitle('Invalid File Error')
            msg.exec_()

        self.update_ui()

    def close_file(self):
        # Session.get_instance().clear()
        self.update_ui()

    def update_ui(self):
        self.widget_data_view.update_ui()
        self.widget_extraction_view.update_ui()
        self.widget_calibration_view.update_ui()

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
        # Session.get_instance().save()
