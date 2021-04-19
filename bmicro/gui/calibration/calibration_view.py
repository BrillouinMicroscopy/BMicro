import pkg_resources
import logging

from PyQt5 import QtWidgets, uic
# from PyQt5.QtWidgets import QMessageBox
from matplotlib.widgets import SpanSelector
import numpy as np

from bmlab.fits import fit_vipa, VIPA
from bmlab.session import Session

from bmicro.gui.mpl import MplCanvas


logger = logging.getLogger(__name__)

MODE_DEFAULT = 'default'
MODE_SELECT_BRILLOUIN = 'select_brillouin_peaks'
MODE_SELECT_RAYLEIGH = 'select_rayleigh_peaks'


class CalibrationView(QtWidgets.QWidget):
    """
    Class for the calibration widget
    """

    def __init__(self, *args, **kwargs):
        super(CalibrationView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.calibration', 'calibration_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget,
                                   toolbar=('Home', 'Pan', 'Zoom'))
        self.plot = self.mplcanvas.get_figure().add_subplot(111)

        rectprops = dict(facecolor='green', alpha=0.5)
        self.span_selector = SpanSelector(
            self.plot, onselect=self.on_select_data_region,
            useblit=True,
            direction='horizontal', rectprops=rectprops)

        self.button_brillouin_select_done.clicked.connect(
            self.on_select_brillouin_clicked)
        self.button_rayleigh_select_done.clicked.connect(
            self.on_select_rayleigh_clicked)
        self.button_brillouin_clear.released.connect(
            self.clear_regions)
        self.button_rayleigh_clear.released.connect(
            self.clear_regions)

        self.button_fit_clear.released.connect(self.clear_fits)

        self.button_calibrate.released.connect(self.calibrate)

        self.current_frame = 0
        self.button_prev_frame.clicked.connect(self.prev_frame)
        self.button_next_frame.clicked.connect(self.next_frame)

        self.mode = MODE_DEFAULT

        self.combobox_calibration.currentIndexChanged.connect(
            self.on_select_calibration)

        self.table_Brillouin_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_BRILLOUIN, item))
        self.table_Rayleigh_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_RAYLEIGH, item))

        self.setupTables()

    def prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            self.refresh_plot()

    def next_frame(self):
        calib_key = self.combobox_calibration.currentText()
        session = Session.get_instance()
        imgs = session.current_repetition().calibration.get_image(calib_key)
        if self.current_frame < len(imgs) - 1:
            self.current_frame += 1
            self.refresh_plot()

    def clear_fits(self):
        session = Session.get_instance()
        cm = session.calibration_model()
        if not cm:
            return

        calib_key = self.combobox_calibration.currentText()
        cm.clear_brillouin_fits(calib_key)
        cm.clear_rayleigh_fits(calib_key)
        self.refresh_plot()

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
        cm = session.calibration_model()
        if not cm:
            return
        calib_key = self.combobox_calibration.currentText()
        if button is self.button_brillouin_clear:
            cm.clear_brillouin_regions(calib_key)
        elif button is self.button_rayleigh_clear:
            cm.clear_rayleigh_regions(calib_key)
        self.refresh_plot()

    def on_select_data_region(self, xmin, xmax):
        if not self.plot.lines[0]:
            return
        # Since we might operate on a frequency axis,
        # we need the indices instead of the values.
        xdata = self.plot.lines[0].get_xdata()
        indmin, indmax = np.searchsorted(xdata, (xmin, xmax))

        if self.mode == MODE_DEFAULT:
            return
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()

        cm = session.calibration_model()
        if cm:
            if self.mode == MODE_SELECT_BRILLOUIN:
                cm.add_brillouin_region(calib_key, (indmin, indmax))
            elif self.mode == MODE_SELECT_RAYLEIGH:
                cm.add_rayleigh_region(calib_key, (indmin, indmax))

        self.refresh_plot()

    def on_select_calibration(self):
        self.refresh_plot()

    def calibrate(self):
        session = Session.get_instance()

        cm = session.calibration_model()
        if not cm:
            return

        setup = session.setup
        if not setup:
            return

        calib_key = self.combobox_calibration.currentText()
        if not calib_key:
            return

        em = session.extraction_model()
        if not em:
            return

        spectra = session.extract_calibration_spectrum(calib_key)

        if spectra is None:
            return

        if len(spectra) == 0:
            return

        session.fit_rayleigh_regions(calib_key)
        session.fit_brillouin_regions(calib_key)

        vipa_params = []
        frequencies = []
        for frame_num, spectrum in enumerate(spectra):
            peaks = cm.get_sorted_peaks(calib_key, frame_num)

            params = fit_vipa(peaks, setup)
            vipa_params.append(params)
            xdata = np.arange(len(spectrum))

            frequencies.append(VIPA(xdata, params) - setup.f0)

        cm.set_vipa_params(calib_key, vipa_params)
        cm.set_frequencies(calib_key, frequencies)

        self.refresh_plot()

    def update_ui(self):
        self.combobox_calibration.clear()
        session = Session.get_instance()

        if not session.file:
            return

        calib_keys = session.current_repetition().calibration.image_keys()
        self.combobox_calibration.addItems(calib_keys)

    def refresh_plot(self):
        self.plot.cla()
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()
        if not calib_key:
            return

        try:
            spectra = session.extract_calibration_spectrum(calib_key)
            if spectra is None:
                return
            spectrum = spectra[self.current_frame]

            cm = session.calibration_model()
            if not cm:
                return

            if len(spectrum) > 0:
                frequencies = cm.get_frequencies_by_calib_key(calib_key)
                frequency = None
                if frequencies:
                    frequency = 1e-9*frequencies[self.current_frame]
                    self.plot.plot(frequency, spectrum)
                    self.plot.set_xlabel('f [GHz]')
                else:
                    self.plot.plot(spectrum)
                    self.plot.set_xlabel('pixels')
                self.plot.set_ylim(bottom=0)
                self.plot.set_title('Frame %d / %d' %
                                    (self.current_frame+1, len(spectra)))

                regions = cm.get_brillouin_regions(calib_key)
                table = self.table_Brillouin_regions
                self.refresh_regions(spectrum, regions, table, 'r', frequency)

                for region_key, region in enumerate(regions):
                    avg_w0 = cm.brillouin_fits.average_fits(
                        calib_key, region_key)
                    if avg_w0 is not None:
                        w0_f = cm.get_frequency_by_calib_key(avg_w0, calib_key)
                        if w0_f is not None:
                            self.plot.vlines(1e-9*w0_f[0], 0, np.nanmax(
                                spectrum), colors=['black'])
                            self.plot.vlines(1e-9*w0_f[1], 0, np.nanmax(
                                spectrum), colors=['black'])
                        else:
                            self.plot.vlines(avg_w0[0], 0, np.nanmax(
                                spectrum), colors=['black'])
                            self.plot.vlines(avg_w0[1], 0, np.nanmax(
                                spectrum), colors=['black'])

                regions = cm.get_rayleigh_regions(calib_key)
                table = self.table_Rayleigh_regions
                self.refresh_regions(spectrum, regions, table, 'm', frequency)

                for region_key, region in enumerate(regions):
                    avg_w0 = cm.rayleigh_fits.average_fits(
                        calib_key, region_key)
                    if avg_w0 is not None:
                        w0_f = cm.get_frequency_by_calib_key(avg_w0, calib_key)
                        if w0_f is not None:
                            self.plot.vlines(1e-9*w0_f, 0, np.nanmax(
                                spectrum), colors=['black'])
                        else:
                            self.plot.vlines(avg_w0, 0, np.nanmax(
                                spectrum), colors=['black'])

        except Exception as e:
            logger.error('Exception occured: %s' % e)
        finally:
            self.mplcanvas.draw()

    def setupTables(self):
        self.table_Brillouin_regions.setColumnCount(2)
        self.table_Brillouin_regions\
            .setHorizontalHeaderLabels(["start", "end"])
        header = self.table_Brillouin_regions.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        self.table_Rayleigh_regions.setColumnCount(2)
        self.table_Rayleigh_regions\
            .setHorizontalHeaderLabels(["start", "end"])
        header = self.table_Rayleigh_regions.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def refresh_regions(self, spectrum, regions, table, color,
                        frequencies=None):
        table.setRowCount(len(regions))
        for rowIdx, region in enumerate(regions):
            mask = np.arange(int(region[0]), int(region[1]))
            if frequencies is not None:
                self.plot.plot(frequencies[mask], spectrum[mask], color)
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
        calib_key = self.combobox_calibration.currentText()

        cm = session.calibration_model()
        if cm:
            if type == MODE_SELECT_BRILLOUIN:
                regions = cm.get_brillouin_regions(calib_key)
                current_region = np.asarray(regions[row])
                current_region[column] = value
                current_region = tuple(current_region)
                cm.set_brillouin_region(calib_key, row, current_region)
            elif type == MODE_SELECT_RAYLEIGH:
                regions = cm.get_rayleigh_regions(calib_key)
                current_region = np.asarray(regions[row])
                current_region[column] = value
                current_region = tuple(current_region)
                cm.set_rayleigh_region(calib_key, row, current_region)
            self.refresh_plot()
