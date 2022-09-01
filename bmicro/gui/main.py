import pathlib
import pkg_resources
import hashlib
import signal
import sys
import traceback

import numpy as np

from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QMessageBox,\
    QVBoxLayout, QWidget, QCheckBox, QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import QSize

from bmlab.session import Session
from bmlab.file import is_source_file
from bmlab.models.setup import AVAILABLE_SETUPS
from bmlab.models import EvaluationModel
from bmlab.controllers import PeakSelectionController, ExportController,\
    EvaluationController

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

        self.imdir = pkg_resources.resource_filename("bmicro", "img")

        self.tabWidget.currentChanged.connect(self.update_ui)

        self.export_dialog = None
        # Initialize the export configuration
        self.export_config = ExportController.get_configuration()

        self.batch_dialog = None
        self.batch_files = {}
        self.batch_config = {
            'setup': {
                'set': False,
                'setup': AVAILABLE_SETUPS[0],
            },
            'orientation': {
                'set': False,
                'rotation': 0,
                'reflection': {'vertically': False, 'horizontally': True},
            },
            'extraction': {
                'extract': False,
            },
            'calibration': {
                'find-peaks': False,
                'calibrate': False,
            },
            'peak-selection': {
                'select': False,
                'brillouin_regions': [(4.0e9, 6.0e9), (9.0e9, 11.0e9)],
                'rayleigh_regions': [(-2.0e9, 2.0e9), (13.0e9, 17.0e9)],
            },
            'evaluation': {
                'evaluate': False,
                'nr_brillouin_peaks': 1,
                'bounds': None,
            },
            'export': {
                'export': False,
            },
        }
        self.batch_evaluation_running = False

        # Build tabs
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

        # Connect drag and drop
        self.dragEnterEvent = self.drag_enter_event
        self.dropEvent = self.drop_event

        self.setAcceptDrops(True)

        self.reset_ui()

        self.settings = QtCore.QSettings()

    def connect_menu(self):
        """ Registers the menu actions """
        self.action_open.triggered.connect(self.open_file)
        self.action_close.triggered.connect(self.close_file)
        self.action_save.triggered.connect(self.save_session)
        self.action_export.triggered.connect(self.on_action_export_file)
        self.action_exit.triggered.connect(self.exit_app)

        self.action_about.triggered.connect(self.on_action_about)
        self.action_batch_evaluation.triggered.connect(
            self.on_action_batch_evaluation)

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
            self.close_file()
            session.set_file(file_name)
        except FileNotFoundError as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText('Unable to load file:')
            msg.setInformativeText(e.strerror)
            msg.setWindowTitle(type(e).__name__)
            msg.exec()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText('An unknown error occured')
            msg.setInformativeText(str(e))
            msg.setWindowTitle('Unknown Error')
            msg.exec()

        self.update_ui()

    def close_file(self):
        Session.get_instance().clear()
        self.reset_ui()

    def on_action_export_file(self):
        ui_file = pkg_resources.resource_filename(
            'bmicro.gui', 'export_configuration.ui')
        self.export_dialog = QtWidgets.QDialog(
            self,
            QtCore.Qt.WindowType.WindowTitleHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        uic.loadUi(ui_file, self.export_dialog)
        self.export_dialog.setWindowTitle('Export configuration')
        self.export_dialog.setWindowModality(
            QtCore.Qt.WindowModality.ApplicationModal)
        self.export_dialog.button_export.clicked.connect(
            self.export_file
        )
        self.export_dialog.button_cancel.clicked.connect(
            self.close_export_dialog
        )
        self.init_export_dialog(self.export_dialog.widget)
        self.export_dialog.resize(QSize(500, 560))

        self.export_dialog.open()

    def on_export_checkbox(self, parameter, min_box, max_box):
        checked = self.sender().isChecked()
        if checked:
            self.export_config['brillouin']['parameters'].append(parameter)
        else:
            self.export_config['brillouin']['parameters'].remove(parameter)
        min_box.setEnabled(checked)
        max_box.setEnabled(checked)

    def on_export_minbox(self, value, parameter):
        cax = [value, 'max']
        # We use the existing upper limit if available
        if parameter in self.export_config['brillouin']:
            cax[1] = self.export_config['brillouin'][parameter]['cax'][1]
        self.export_config['brillouin'][parameter]['cax'] = tuple(cax)

    def on_export_maxbox(self, value, parameter):
        cax = ['min', value]
        # We use the existing lower limit if available
        if parameter in self.export_config['brillouin']:
            cax[0] = self.export_config['brillouin'][parameter]['cax'][0]
        self.export_config['brillouin'][parameter]['cax'] = tuple(cax)

    def init_export_dialog(self, parent_widget):
        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 6, 0, 6)
        v_layout.setSpacing(0)

        parameters = EvaluationModel.get_default_parameters()
        for key, parameter in parameters.items():
            h_layout = QHBoxLayout()

            # Checkbox
            checkbox = QCheckBox()
            checkbox.setText(
                parameter['label'] + ' [' + parameter['unit'] + ']')
            if key in self.export_config['brillouin']['parameters']:
                checkbox.setChecked(True)
            h_layout.addWidget(checkbox)
            # Spacer
            h_layout.addStretch()

            # Min label and input box
            min_label = QLabel()
            min_label.setText('min')
            h_layout.addWidget(min_label)
            min_box = QLineEdit()
            min_box.setMaximumSize(QSize(50, 20))
            min_box.setMinimumSize(QSize(50, 20))
            h_layout.addWidget(min_box)

            # Max label and input box
            max_label = QLabel()
            max_label.setText('max')
            h_layout.addWidget(max_label)
            max_box = QLineEdit()
            max_box.setMaximumSize(QSize(50, 20))
            max_box.setMinimumSize(QSize(50, 20))
            h_layout.addWidget(max_box)

            # Widget to add the elements to
            parameter_widget = QWidget()
            parameter_widget.setMaximumSize(QSize(5000, 35))
            parameter_widget.setLayout(h_layout)
            v_layout.addWidget(parameter_widget)

            # Set the current config values
            if key in self.export_config['brillouin']:
                min_box.setText(self.export_config['brillouin'][key]['cax'][0])
                max_box.setText(self.export_config['brillouin'][key]['cax'][1])
            # Otherwise we set it to the default min/max
            else:
                min_box.setText('min')
                max_box.setText('max')

            if key in self.export_config['brillouin']['parameters']:
                checkbox.setChecked(True)
                min_box.setEnabled(True)
                max_box.setEnabled(True)
            else:
                min_box.setEnabled(False)
                max_box.setEnabled(False)

            # Connect handlers
            checkbox.clicked.connect(
                lambda checked, param=key, minbox=min_box, maxbox=max_box:
                self.on_export_checkbox(param, minbox, maxbox)
            )
            min_box.textChanged.connect(
                lambda value, param=key: self.on_export_minbox(value, param)
            )
            max_box.textChanged.connect(
                lambda value, param=key: self.on_export_maxbox(value, param)
            )

        # This only works if there is no layout set yet!
        parent_widget.setLayout(v_layout)
        # self.export_dialog.scrollAreaWidgetContents.\
        #     setMinimumSize(QSize(0, 40*len(parameters)))

    def close_export_dialog(self):
        self.export_dialog.close()

    def export_file(self):
        ExportController().export(self.export_config)

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

    @staticmethod
    def drag_enter_event(event):
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

    @staticmethod
    def save_session():
        """ Save the session data to file with ending '.bms' """
        Session.get_instance().save()

    @staticmethod
    def exit_app():
        QtCore.QCoreApplication.quit()

    def on_action_about(self):
        gh = "BrillouinMicroscopy/BMicro"
        rtd = "bmicro.readthedocs.io"
        about_text = f"BMicro {bmicroversion}<br><br>" \
            + "BMicro is a graphical user interface " \
            + "for the analysis of Brillouin microscopy data.<br><br>" \
            + f"Using bmlab {bmlabversion}<br><br>" \
            + "Author: Raimund Schlüßler and others<br>" \
            + "GitHub: " \
            + "<a href='https://github.com/{gh}'>{gh}</a><br>".format(gh=gh) \
            + "Documentation: " \
            + "<a href='https://{rtd}'>{rtd}</a><br>".format(rtd=rtd)
        QtWidgets.QMessageBox.about(self,
                                    f"BMicro {bmicroversion}", about_text)

    def on_action_batch_evaluation(self):
        ui_file = pkg_resources.resource_filename(
            'bmicro.gui', 'batch_evaluation.ui')
        self.batch_dialog = QtWidgets.QDialog(
            self,
            QtCore.Qt.WindowType.WindowTitleHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint
        )
        uic.loadUi(ui_file, self.batch_dialog)
        self.batch_dialog.setWindowTitle('Batch evaluation')
        self.batch_dialog.setWindowModality(
            QtCore.Qt.WindowModality.ApplicationModal)
        self.batch_dialog.button_start_cancel.clicked.connect(
            self.start_batch_evaluation
        )
        self.batch_dialog.button_add_folder.clicked.connect(
            self.batch_add_files
        )
        self.batch_dialog.button_remove_folder.clicked.connect(
            self.batch_remove_files
        )
        self.update_batch_file_table()
        self.init_export_dialog(self.batch_dialog.widget_parameters)
        self.batch_dialog.adjustSize()

        self.update_batch_file_settings()

        self.batch_dialog.exec()

    def close_batch_dialog(self):
        self.batch_dialog.close()

    def update_batch_file_settings(self):
        # Setup
        cfg_setup = self.batch_config['setup']
        self.batch_dialog.checkBox_setup.setChecked(cfg_setup['set'])
        self.batch_dialog.checkBox_setup.clicked.connect(self.on_setup_set)
        self.batch_dialog.combobox_setup.addItems(
            [s.name for s in AVAILABLE_SETUPS])
        idx = AVAILABLE_SETUPS.index(cfg_setup['setup'])
        if idx:
            self.batch_dialog.combobox_setup.setCurrentIndex(idx)
        self.batch_dialog.combobox_setup.setEnabled(cfg_setup['set'])
        self.batch_dialog.combobox_setup.currentIndexChanged.connect(
            self.on_setup_select)

        # Orientation
        cfg_orientation = self.batch_config['orientation']
        self.batch_dialog.checkBox_orientation\
            .setChecked(cfg_orientation['set'])
        self.batch_dialog.checkBox_orientation\
            .clicked.connect(self.on_orientation_set)
        self.batch_dialog.groupBox_rotation\
            .setEnabled(cfg_orientation['set'])
        self.batch_dialog.groupBox_reflection\
            .setEnabled(cfg_orientation['set'])

        self.batch_dialog.checkbox_reflect_vertically.setChecked(
            cfg_orientation['reflection']['vertically'])
        self.batch_dialog.checkbox_reflect_horizontally.setChecked(
            cfg_orientation['reflection']['horizontally'])

        self.batch_dialog.radio_rotation_none.setChecked(
            cfg_orientation['rotation'] % 4 == 0)
        self.batch_dialog.radio_rotation_90_cw.setChecked(
            cfg_orientation['rotation'] % 4 == 1)
        self.batch_dialog.radio_rotation_90_ccw.setChecked(
            cfg_orientation['rotation'] % 4 == 3)

        self.batch_dialog.radio_rotation_none\
            .clicked.connect(self.on_rotation_clicked)
        self.batch_dialog.radio_rotation_90_cw\
            .clicked.connect(self.on_rotation_clicked)
        self.batch_dialog.radio_rotation_90_ccw\
            .clicked.connect(self.on_rotation_clicked)

        self.batch_dialog.checkbox_reflect_vertically.toggled.connect(
            self.on_reflection_clicked)
        self.batch_dialog.checkbox_reflect_horizontally.toggled.connect(
            self.on_reflection_clicked)

        # Extraction
        cfg_extraction = self.batch_config['extraction']
        self.batch_dialog.checkBox_extraction\
            .setChecked(cfg_extraction['extract'])
        self.batch_dialog.checkBox_extraction\
            .clicked.connect(self.on_extraction_set)

        # Calibration
        cfg_calibration = self.batch_config['calibration']
        self.batch_dialog.checkBox_find_peaks\
            .setChecked(cfg_calibration['find-peaks'])
        self.batch_dialog.checkBox_find_peaks\
            .clicked.connect(self.on_calibration_find_peaks)
        self.batch_dialog.checkBox_calibrate\
            .setChecked(cfg_calibration['calibrate'])
        self.batch_dialog.checkBox_calibrate\
            .clicked.connect(self.on_calibration_calibrate)

        # Peak selection
        cfg_peak_selection = self.batch_config['peak-selection']
        self.batch_dialog.checkBox_peak_selection\
            .setChecked(cfg_peak_selection['select'])
        self.batch_dialog.checkBox_peak_selection\
            .clicked.connect(self.on_peak_selection_select)
        self.batch_dialog.tableWidget_Brillouin\
            .setEnabled(cfg_peak_selection['select'])
        self.batch_dialog.tableWidget_Rayleigh\
            .setEnabled(cfg_peak_selection['select'])
        self.batch_dialog.button_region_brillouin_remove.clicked.connect(
            lambda: self.remove_evaluation_regions(
                self.batch_dialog.tableWidget_Brillouin,
                self.batch_config[
                    'peak-selection']['brillouin_regions']
            )
        )
        self.batch_dialog.button_region_brillouin_add.clicked.connect(
            lambda: self.add_evaluation_regions(
                self.batch_dialog.tableWidget_Brillouin,
                self.batch_config[
                    'peak-selection']['brillouin_regions']
            )
        )
        self.batch_dialog.button_region_rayleigh_remove.clicked.connect(
            lambda: self.remove_evaluation_regions(
                self.batch_dialog.tableWidget_Rayleigh,
                self.batch_config[
                    'peak-selection']['rayleigh_regions']
            )
        )
        self.batch_dialog.button_region_rayleigh_add.clicked.connect(
            lambda: self.add_evaluation_regions(
                self.batch_dialog.tableWidget_Rayleigh,
                self.batch_config[
                    'peak-selection']['rayleigh_regions']
            )
        )

        self.update_evaluation_regions_tables()

        self.batch_dialog.tableWidget_Brillouin.itemChanged.connect(
            lambda item: self.on_region_changed(
                self.batch_config['peak-selection']['brillouin_regions'],
                item)
        )

        self.batch_dialog.tableWidget_Rayleigh.itemChanged.connect(
            lambda item: self.on_region_changed(
                self.batch_config['peak-selection']['rayleigh_regions'],
                item)
        )

        header = self.batch_dialog.tableWidget_Brillouin.horizontalHeader()
        header.setSectionResizeMode(0,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.batch_dialog.tableWidget_Brillouin\
            .verticalHeader().setVisible(False)
        self.batch_dialog.tableWidget_Brillouin \
            .setHorizontalHeaderLabels(["start", "end"])

        header = self.batch_dialog.tableWidget_Rayleigh.horizontalHeader()
        header.setSectionResizeMode(0,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.batch_dialog.tableWidget_Rayleigh\
            .verticalHeader().setVisible(False)
        self.batch_dialog.tableWidget_Rayleigh\
            .setHorizontalHeaderLabels(["start", "end"])

        # Evaluation
        cfg_evaluation = self.batch_config['evaluation']
        self.batch_dialog.checkBox_evaluation\
            .setChecked(cfg_evaluation['evaluate'])
        self.batch_dialog.checkBox_evaluation\
            .clicked.connect(self.on_evaluation_evaluate)
        self.batch_dialog.nrBrillouinPeaksGroup\
            .setEnabled(cfg_evaluation['evaluate'])
        if cfg_evaluation['nr_brillouin_peaks'] == 1:
            self.batch_dialog.nrBrillouinPeaks_1.setChecked(True)
        else:
            self.batch_dialog.nrBrillouinPeaks_2.setChecked(True)
        self.batch_dialog.bounds_table\
            .setEnabled(cfg_evaluation['evaluate'] and
                        cfg_evaluation['nr_brillouin_peaks'] > 1)

        self.batch_dialog.bounds_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.batch_dialog.bounds_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.update_batch_bounds_table()
        self.batch_dialog.bounds_table.cellChanged.connect(
            self.evaluation_bounds_changed)

        self.batch_dialog.nrBrillouinPeaks_1.toggled.connect(
            lambda: self.set_nr_brillouin_peaks(1))
        self.batch_dialog.nrBrillouinPeaks_2.toggled.connect(
            lambda: self.set_nr_brillouin_peaks(2))

        # Export
        cfg_export = self.batch_config['export']
        self.batch_dialog.checkBox_export\
            .setChecked(cfg_export['export'])
        self.batch_dialog.checkBox_export\
            .clicked.connect(self.on_export_export)

    def update_batch_bounds_table(self):
        bounds = self.batch_config['evaluation']['bounds']
        if bounds is None:
            self.batch_dialog.bounds_table.setRowCount(0)
        else:
            self.batch_dialog.bounds_table.setColumnCount(2)
            self.batch_dialog.bounds_table.setRowCount(len(bounds))
            for i, bound in enumerate(bounds):
                item = QtWidgets.QTableWidgetItem(str(bound[0]))
                self.batch_dialog.bounds_table.setItem(i, 0, item)
                item = QtWidgets.QTableWidgetItem(str(bound[1]))
                self.batch_dialog.bounds_table.setItem(i, 1, item)

        self.batch_dialog.bounds_table.setEnabled(
            self.batch_config['evaluation']['evaluate'] and
            self.batch_config['evaluation']['nr_brillouin_peaks'] > 1)

    def set_nr_brillouin_peaks(self, nr_peaks):
        if not self.sender().isChecked():
            return
        self.batch_config['evaluation']['nr_brillouin_peaks'] = nr_peaks

        if nr_peaks == 1:
            bounds = None

        # Initialize the bounds if necessary
        if nr_peaks > 1 and\
                (self.batch_config['evaluation']['bounds'] is None or
                 len(self.batch_config['evaluation']['bounds'])
                 is not nr_peaks):
            bounds = [['min', 'max'] for _ in range(nr_peaks)]

        self.batch_config['evaluation']['bounds'] = bounds

        self.update_batch_bounds_table()

    def evaluation_bounds_changed(self, row, column):
        self.batch_config['evaluation']['bounds'][row][column] =\
                self.batch_dialog.bounds_table.item(row, column).text()

    def add_evaluation_regions(self, region_table, region_list):
        region_list.append((0., 0.))

        self.update_evaluation_regions_tables()

        region_table.setFocus()
        region_table.setCurrentCell(len(region_list) - 1, 0)

    def remove_evaluation_regions(self, region_table, region_list):
        selected_ranges = region_table.selectedRanges()
        sorted_ranges = sorted(
            selected_ranges,
            key=lambda item: item.topRow(),
            reverse=True
        )
        for sorted_range in sorted_ranges:
            start = sorted_range.topRow()
            end = sorted_range.bottomRow()
            for idx in reversed(range(start, end + 1)):
                del region_list[idx]
        region_table.clearSelection()

        self.update_evaluation_regions_tables()

    def update_evaluation_regions_tables(self):
        cfg_peak_selection = self.batch_config['peak-selection']

        brillouin_regions = cfg_peak_selection['brillouin_regions']
        brillouin_table = self.batch_dialog.tableWidget_Brillouin
        brillouin_table.setRowCount(len(brillouin_regions))
        for rowIdx, region in enumerate(brillouin_regions):
            # Add regions to table
            # Block signals, so the itemChanged signal is not
            # emitted during table creation
            brillouin_table.blockSignals(True)
            for columnIdx, value in enumerate(region):
                region_item = QtWidgets.QTableWidgetItem(str(1e-9 * value))
                brillouin_table.setItem(rowIdx, columnIdx, region_item)
            brillouin_table.blockSignals(False)

        rayleigh_regions = cfg_peak_selection['rayleigh_regions']
        rayleigh_table = self.batch_dialog.tableWidget_Rayleigh
        rayleigh_table.setRowCount(len(rayleigh_regions))
        for rowIdx, region in enumerate(rayleigh_regions):
            # Add regions to table
            # Block signals, so the itemChanged signal is not
            # emitted during table creation
            rayleigh_table.blockSignals(True)
            for columnIdx, value in enumerate(region):
                region_item = QtWidgets.QTableWidgetItem(str(1e-9 * value))
                rayleigh_table.setItem(rowIdx, columnIdx, region_item)
            rayleigh_table.blockSignals(False)

    def on_setup_set(self):
        self.batch_config['setup']['set'] = self.sender().isChecked()
        self.batch_dialog.combobox_setup\
            .setEnabled(self.batch_config['setup']['set'])

    def on_orientation_set(self):
        self.batch_config['orientation']['set'] = self.sender().isChecked()
        self.batch_dialog.groupBox_rotation\
            .setEnabled(self.batch_config['orientation']['set'])
        self.batch_dialog.groupBox_reflection\
            .setEnabled(self.batch_config['orientation']['set'])

    def on_rotation_clicked(self):
        """
        Action triggered when user clicks one of the rotation radio buttons.
        """

        radio_button = self.sender()
        if not radio_button.isChecked():
            return

        if radio_button == self.batch_dialog.radio_rotation_none:
            self.batch_config['orientation']['rotation'] = 0
        elif radio_button == self.batch_dialog.radio_rotation_90_cw:
            self.batch_config['orientation']['rotation'] = 1
        elif radio_button == self.batch_dialog.radio_rotation_90_ccw:
            self.batch_config['orientation']['rotation'] = 3

    def on_reflection_clicked(self):
        """ Triggered when a reflection checkbox is clicked """

        checkbox = self.sender()

        if checkbox == self.batch_dialog.checkbox_reflect_vertically:
            self.batch_config['orientation'][
                'reflection']['vertically'] = checkbox.isChecked()
        elif checkbox == self.batch_dialog.checkbox_reflect_horizontally:
            self.batch_config['orientation'][
                'reflection']['horizontally'] = checkbox.isChecked()

    def on_extraction_set(self):
        self.batch_config['extraction']['extract'] = self.sender().isChecked()

    def on_calibration_find_peaks(self):
        self.batch_config['calibration']['find-peaks']\
            = self.sender().isChecked()

    def on_calibration_calibrate(self):
        self.batch_config['calibration']['calibrate']\
            = self.sender().isChecked()

    def on_peak_selection_select(self):
        self.batch_config['peak-selection']['select']\
            = self.sender().isChecked()
        self.batch_dialog.tableWidget_Brillouin\
            .setEnabled(self.batch_config['peak-selection']['select'])
        self.batch_dialog.tableWidget_Rayleigh\
            .setEnabled(self.batch_config['peak-selection']['select'])

    @staticmethod
    def on_region_changed(region_table, item):
        row = item.row()
        column = item.column()
        value = float(item.text())

        current_region = np.asarray(region_table[row])
        current_region[column] = 1e9 * value
        current_region = tuple(current_region)
        region_table[row] = current_region

    def on_evaluation_evaluate(self):
        self.batch_config['evaluation']['evaluate']\
            = self.sender().isChecked()
        self.batch_dialog.nrBrillouinPeaksGroup\
            .setEnabled(self.batch_config['evaluation']['evaluate'])
        self.batch_dialog.bounds_table\
            .setEnabled(
                self.batch_config['evaluation']['evaluate'] and
                self.batch_config['evaluation']['nr_brillouin_peaks'] > 1)

    def on_export_export(self):
        self.batch_config['export']['export'] = self.sender().isChecked()

    def on_setup_select(self):
        """
        Action triggered when the user selects a different setup.
        """
        name = self.batch_dialog.combobox_setup.currentText()
        setup = None
        for s in AVAILABLE_SETUPS:
            if s.name == name:
                setup = s
                break
        self.batch_config['setup']['setup'] = setup

    def start_batch_evaluation(self):
        self.batch_evaluation_running = not self.batch_evaluation_running
        if self.batch_evaluation_running:
            self.run_batch_evaluation()
        else:
            self.widget_evaluation_view.evaluation_abort.value = True

    def run_batch_evaluation(self):
        self.batch_dialog.button_start_cancel.setText('Cancel')
        self.batch_dialog.progressBar.setMaximum(len(self.batch_files))
        self.batch_dialog.progressBar.setValue(0)
        for i, (file_hash, file) in enumerate(self.batch_files.items()):
            try:
                self.evaluate_batch_file(file)
            except BaseException:
                # Set the status as failed
                file['status'] = 'failed'
                self.update_batch_file_table()
            if not self.batch_evaluation_running:
                break
            self.batch_dialog.progressBar.setValue(i + 1)
        self.batch_dialog.button_start_cancel.setText('Start')
        self.batch_evaluation_running = False
        self.update_batch_file_table()

    def evaluate_batch_file(self, file):
        # Set the status as in process
        file['status'] = 'in-process'
        self.update_batch_file_table()

        # Show the data tab and open the file
        self.tabWidget.setCurrentIndex(0)
        QtCore.QCoreApplication.instance().processEvents()
        self.open_file(file['path'])
        QtCore.QCoreApplication.instance().processEvents()

        """
        Evaluate the file
        """
        session = Session.get_instance()

        rep_keys = session.file.repetition_keys()

        for rep_key in rep_keys:
            # Load repetition
            session.set_current_repetition(rep_key)
            QtCore.QCoreApplication.instance().processEvents()

            # Setup
            cfg_setup = self.batch_config['setup']
            if cfg_setup['set']:
                session.set_setup(cfg_setup['setup'])

            # Orientation
            cfg_orientation = self.batch_config['orientation']
            if cfg_orientation['set']:
                session.set_rotation(cfg_orientation['rotation'])
                session.set_reflection(
                    vertically=cfg_orientation['reflection']['vertically'],
                    horizontally=cfg_orientation['reflection']['horizontally']
                )

            # Exctraction
            cfg_extraction = self.batch_config['extraction']
            if cfg_extraction['extract']:
                self.tabWidget.setCurrentIndex(1)
                if self.aborted(file):
                    return
                QtCore.QCoreApplication.instance().processEvents()
                self.widget_extraction_view.find_points_all()

            # Calibration
            cfg_calibration = self.batch_config['calibration']
            if cfg_calibration['find-peaks'] or\
                    cfg_calibration['calibrate']:
                self.tabWidget.setCurrentIndex(2)
                if self.aborted(file):
                    return
                QtCore.QCoreApplication.instance().processEvents()
                if not cfg_calibration['find-peaks']:
                    self.widget_calibration_view.\
                        calibrate_all(do_not='find_peaks')
                elif not cfg_calibration['calibrate']:
                    self.widget_calibration_view.\
                        calibrate_all(do_not='calibrate')
                else:
                    self.widget_calibration_view.calibrate_all()

            # PeakSelection
            cfg_peak_selection = self.batch_config['peak-selection']
            if cfg_peak_selection['select']:
                self.tabWidget.setCurrentIndex(3)
                if self.aborted(file):
                    return
                QtCore.QCoreApplication.instance().processEvents()
                psc = PeakSelectionController()
                for brillouin_region \
                        in cfg_peak_selection['brillouin_regions']:
                    psc.add_brillouin_region_frequency(brillouin_region)
                for rayleigh_region \
                        in cfg_peak_selection['rayleigh_regions']:
                    psc.add_rayleigh_region_frequency(rayleigh_region)
                self.widget_peak_selection_view.update_ui()
                QtCore.QCoreApplication.instance().processEvents()

            # Evaluation
            cfg_evaluation = self.batch_config['evaluation']
            if cfg_evaluation['evaluate']:
                self.tabWidget.setCurrentIndex(4)
                if self.aborted(file):
                    return
                QtCore.QCoreApplication.instance().processEvents()
                evc = EvaluationController()
                evc.set_nr_brillouin_peaks(
                    cfg_evaluation['nr_brillouin_peaks'])
                evc.set_bounds(cfg_evaluation['bounds'])
                self.widget_evaluation_view.evaluate(blocking=True)

            cfg_export = self.batch_config['export']
            if cfg_export['export']:
                if self.aborted(file):
                    return
                QtCore.QCoreApplication.instance().processEvents()
                self.export_file()

        # Save the evaluated data
        self.save_session()
        if self.aborted(file):
            return
        QtCore.QCoreApplication.instance().processEvents()

        # Close the file
        self.close_file()
        QtCore.QCoreApplication.instance().processEvents()

        # Set the status as done
        file['status'] = 'success'
        self.update_batch_file_table()

    def aborted(self, file):
        if not self.batch_evaluation_running:
            file['status'] = 'aborted'
            self.close_file()
            self.batch_evaluation_running = False
            self.update_batch_file_table()
            self.batch_dialog.progressBar.setValue(0)
            QtCore.QCoreApplication.instance().processEvents()
            return True

    def batch_add_files(self):
        folder_name = QFileDialog.getExistingDirectory(
            self, 'Select folder...',
            directory=self.settings.value("path/last-used")
        )

        if not folder_name:
            return

        # Find all h5 files in the selected folder
        h5_files = pathlib.Path(folder_name).glob('**/*.h5')

        # Add source files to batch if not present yet
        for h5_file in h5_files:
            h5_file_md5 = hashlib.md5(str(h5_file).encode('utf-8')).hexdigest()
            if is_source_file(h5_file)\
                    and h5_file_md5 not in self.batch_files:
                self.batch_files[h5_file_md5] = {
                    'path': h5_file,
                    'status': 'pending',
                }

        self.update_batch_file_table()

    def batch_remove_files(self):
        table = self.batch_dialog.table_files
        selected_ranges = table.selectedRanges()
        hashes = list(self.batch_files.keys())
        hashes_remove = []
        for selected_range in selected_ranges:
            start = selected_range.topRow()
            end = selected_range.bottomRow()
            for i in range(start, end + 1):
                hashes_remove.append(hashes[i])
        for hash_remove in hashes_remove:
            self.batch_files.pop(hash_remove)
        table.clearSelection()
        self.update_batch_file_table()

    def update_batch_file_table(self):
        table = self.batch_dialog.table_files
        table.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        table.setWordWrap(False)
        table.setColumnCount(2)
        table.setRowCount(len(self.batch_files))
        table.blockSignals(True)

        pending_icon_path = str(pathlib.Path(self.imdir) / "pending.svg")
        inprocess_icon_path = str(pathlib.Path(self.imdir) / "in-process.svg")
        success_icon_path =\
            str(pathlib.Path(self.imdir) / "check_circle_outline.svg")
        failed_icon_path = str(pathlib.Path(self.imdir) / "error.svg")
        aborted_icon_path = str(pathlib.Path(self.imdir) / "cancel.svg")

        for rowIdx, (file_hash, file) in enumerate(self.batch_files.items()):
            table.setIconSize(QtCore.QSize(20, 20))
            status = file['status']
            if status == 'in-process':
                icon_path = inprocess_icon_path
            elif status == 'success':
                icon_path = success_icon_path
            elif status == 'aborted':
                icon_path = aborted_icon_path
            elif status == 'failed':
                icon_path = failed_icon_path
            else:
                icon_path = pending_icon_path
            icon = QtGui.QIcon(icon_path)
            entry = QtWidgets.QTableWidgetItem()
            entry.setSizeHint(QtCore.QSize(20, 20))
            entry.setIcon(icon)
            table.setItem(rowIdx, 0, entry)

            path = QtWidgets.QTableWidgetItem(str(file['path']))
            table.setItem(rowIdx, 1, path)
        table.setColumnWidth(0, 18)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setVisible(False)
        table.blockSignals(False)


def excepthook(etype, value, trace):
    """
    Handler for all unhandled exceptions.
    Parameters
    ----------
    etype: Exception
        the exception type (`SyntaxError`,
        `ZeroDivisionError`, etc...)
    value: str
        the exception error message
    trace: str
        the traceback header, if any (otherwise, it
        prints the standard Python header: ``Traceback (most recent
        call last)``.
    """
    vinfo = "Unhandled exception in BMicro version {}:\n".format(
        bmicroversion)
    tmp = traceback.format_exception(etype, value, trace)
    exception = "".join([vinfo]+tmp)

    errorbox = QtWidgets.QMessageBox()
    errorbox.addButton(QtWidgets.QPushButton('Close'),
                       QtWidgets.QMessageBox.ButtonRole.YesRole)
    errorbox.addButton(QtWidgets.QPushButton(
        'Copy text && Close'), QtWidgets.QMessageBox.ButtonRole.NoRole)
    errorbox.setText(exception)
    ret = errorbox.exec()
    if ret == 1:
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Mode.Clipboard)
        cb.setText(exception)


# Make Ctr+C close the app
signal.signal(signal.SIGINT, signal.SIG_DFL)
# Display exception hook in separate dialog instead of crashing
sys.excepthook = excepthook
