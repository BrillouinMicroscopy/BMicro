import pkg_resources
import logging

from PyQt6 import QtWidgets, uic

from matplotlib.widgets import SpanSelector
import numpy as np

from bmlab.session import Session
from bmlab.controllers import EvaluationController

from bmicro.gui.mpl import MplCanvas
import warnings

logger = logging.getLogger(__name__)

MODE_DEFAULT = 'default'
MODE_SELECT_BRILLOUIN = 'select_brillouin_peaks'
MODE_SELECT_RAYLEIGH = 'select_rayleigh_peaks'


class PeakSelectionView(QtWidgets.QWidget):
    """
    Class for the peak selection widget
    """

    def __init__(self, *args, **kwargs):
        super(PeakSelectionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.peak_selection', 'peak_selection_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget,
                                   toolbar=('Home', 'Pan', 'Zoom'))
        self.plot = self.mplcanvas.get_figure().add_subplot(111)

        props = dict(facecolor='green', alpha=0.5)
        self.span_selector = SpanSelector(
            self.plot, onselect=self.on_select_data_region,
            useblit=True,
            direction='horizontal', props=props)

        self.button_brillouin_select_done.clicked.connect(
            self.on_select_brillouin_clicked)
        self.button_rayleigh_select_done.clicked.connect(
            self.on_select_rayleigh_clicked)
        self.button_brillouin_clear.released.connect(
            self.clear_regions)
        self.button_rayleigh_clear.released.connect(
            self.clear_regions)

        self.mode = MODE_DEFAULT

        self.table_Brillouin_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_BRILLOUIN, item))
        self.table_Rayleigh_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_RAYLEIGH, item))

        self.setupTables()

        self.update_ui()

    def update_ui(self):
        self.refresh_plot()

    def reset_ui(self):
        self.table_Brillouin_regions.setRowCount(0)
        self.table_Rayleigh_regions.setRowCount(0)
        self.plot.cla()
        self.mplcanvas.draw()

    def on_select_brillouin_clicked(self):
        if self.mode == MODE_SELECT_BRILLOUIN:
            self.mode = MODE_DEFAULT
            self.button_brillouin_select_done.setText('Select')
            self.button_rayleigh_select_done.setText('Select')
        else:
            self.mode = MODE_SELECT_BRILLOUIN
            self.button_brillouin_select_done.setText('Done')
            self.button_rayleigh_select_done.setText('Select')

    def on_select_rayleigh_clicked(self):
        if self.mode == MODE_SELECT_RAYLEIGH:
            self.mode = MODE_DEFAULT
            self.button_brillouin_select_done.setText('Select')
            self.button_rayleigh_select_done.setText('Select')
        else:
            self.mode = MODE_SELECT_RAYLEIGH
            self.button_brillouin_select_done.setText('Select')
            self.button_rayleigh_select_done.setText('Done')

    def clear_regions(self):
        button = self.sender()
        session = Session.get_instance()
        pm = session.peak_selection_model()
        if not pm:
            return
        if button is self.button_brillouin_clear:
            pm.clear_brillouin_regions()
        elif button is self.button_rayleigh_clear:
            pm.clear_rayleigh_regions()
        self.refresh_plot()

    def on_select_data_region(self, xmin, xmax):
        if not self.plot.lines or not self.plot.lines[0]:
            return
        # Since we might operate on a frequency axis,
        # we need the indices instead of the values.
        xdata = self.plot.lines[0].get_xdata()
        indmin, indmax = np.searchsorted(xdata, (xmin, xmax))

        if self.mode == MODE_DEFAULT:
            return
        session = Session.get_instance()

        pm = session.peak_selection_model()
        if pm:
            if self.mode == MODE_SELECT_BRILLOUIN:
                pm.add_brillouin_region((indmin, indmax))
            elif self.mode == MODE_SELECT_RAYLEIGH:
                pm.add_rayleigh_region((indmin, indmax))

        self.refresh_plot()

    def refresh_plot(self):
        self.plot.cla()
        session = Session.get_instance()
        evc = EvaluationController()

        try:
            image_key = '0'
            spectrum, times, _ = evc.extract_spectra(
                image_key
            )
            if spectrum is None:
                return

            cm = session.calibration_model()
            if not cm:
                return

            pm = session.peak_selection_model()
            if not pm:
                return

            if len(spectrum) > 0:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        action='ignore',
                        message='Mean of empty slice'
                    )
                    spectrum = np.nanmean(spectrum, 0)
                time = times[0]
                frequencies = cm.get_frequencies_by_time(time)
                if frequencies is not None:
                    self.plot.plot(1e-9*frequencies, spectrum)
                    self.plot.set_xlabel('$f$ [GHz]')
                    self.plot.set_xlim(1e-9*np.min(frequencies),
                                       1e-9*np.max(frequencies))
                else:
                    self.plot.plot(spectrum)
                    self.plot.set_xlabel('$f$ [pix]')
                    self.plot.set_xlim(0, len(spectrum))
                self.plot.set_ylim(bottom=0)

                regions = pm.get_brillouin_regions()
                table = self.table_Brillouin_regions
                self.refresh_regions(
                    spectrum, regions, table, 'r', frequencies)

                regions = pm.get_rayleigh_regions()
                table = self.table_Rayleigh_regions
                self.refresh_regions(
                    spectrum, regions, table, 'm', frequencies)

        except Exception as e:
            logger.error('Exception occurred in peak selection: %s' % e)
        finally:
            self.mplcanvas.draw()

    def setupTables(self):
        self.table_Brillouin_regions.setColumnCount(2)
        self.table_Brillouin_regions\
            .setHorizontalHeaderLabels(["start", "end"])
        header = self.table_Brillouin_regions.horizontalHeader()
        header.setSectionResizeMode(0,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.table_Rayleigh_regions.setColumnCount(2)
        self.table_Rayleigh_regions\
            .setHorizontalHeaderLabels(["start", "end"])
        header = self.table_Rayleigh_regions.horizontalHeader()
        header.setSectionResizeMode(0,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)

    def refresh_regions(self, spectrum, regions, table, color,
                        frequencies=None):
        table.setRowCount(len(regions))
        for rowIdx, region in enumerate(regions):
            mask = np.arange(int(region[0]), int(region[1]))
            if frequencies is not None:
                self.plot.plot(1e-9*frequencies[mask], spectrum[mask], color)
            else:
                self.plot.plot(mask, spectrum[mask], color)
            # Add regions to table
            # Block signals, so the itemChanged signal is not
            # emitted during table creation
            table.blockSignals(True)
            for columnIdx, value in enumerate(region):
                item = QtWidgets.QTableWidgetItem(str(value))
                table.setItem(rowIdx, columnIdx, item)
            table.blockSignals(False)

    def on_region_changed(self, type, item):
        row = item.row()
        column = item.column()
        value = float(item.text())

        session = Session.get_instance()

        pm = session.peak_selection_model()
        if pm:
            if type == MODE_SELECT_BRILLOUIN:
                regions = pm.get_brillouin_regions()
                current_region = np.asarray(regions[row])
                current_region[column] = value
                current_region = tuple(current_region)
                pm.set_brillouin_region(row, current_region)
            elif type == MODE_SELECT_RAYLEIGH:
                regions = pm.get_rayleigh_regions()
                current_region = np.asarray(regions[row])
                current_region[column] = value
                current_region = tuple(current_region)
                pm.set_rayleigh_region(row, current_region)
            self.refresh_plot()
