import pkg_resources
import logging

from PyQt6 import QtWidgets, QtCore, uic
# from PyQt6.QtWidgets import QMessageBox
from matplotlib.widgets import SpanSelector
import numpy as np
import multiprocessing as mp
import time

from bmlab.session import Session

from bmlab.controllers import CalibrationController

from bmicro.BGThread import BGThread
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

        self.thread = BGThread()

        props = dict(facecolor='green', alpha=0.5)
        self.span_selector = SpanSelector(
            self.plot, onselect=self.on_select_data_region,
            useblit=True,
            direction='horizontal', props=props)

        self.button_find_peaks.clicked.connect(self.find_peaks)

        self.button_brillouin_select_done.clicked.connect(
            self.on_select_brillouin_clicked)
        self.button_rayleigh_select_done.clicked.connect(
            self.on_select_rayleigh_clicked)
        self.button_brillouin_clear.released.connect(
            self.clear_regions)
        self.button_rayleigh_clear.released.connect(
            self.clear_regions)

        self.button_fit_clear.released.connect(self.clear_calibration)

        self.button_calibrate.released.connect(self.calibrate)

        self.button_find_peaks_all.released.connect(
            lambda: self.calibrate_all(do_not='calibrate'))
        self.button_calibrate_all.released.connect(
            lambda: self.calibrate_all(do_not='find_peaks'))
        self.button_peaks_and_calibrate_all\
            .released.connect(self.calibrate_all)

        self.current_frame = 0
        self.button_prev_frame.clicked.connect(self.prev_frame)
        self.button_next_frame.clicked.connect(self.next_frame)

        self.options_dialog = None
        self.mplcanvas_options = None
        self.plot_options = None
        self.calibration_options.clicked.connect(self.show_options)

        self.mode = MODE_DEFAULT

        self.combobox_calibration.currentIndexChanged.connect(
            self.on_select_calibration)

        self.table_Brillouin_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_BRILLOUIN, item))
        self.table_Rayleigh_regions.itemChanged.connect(
            lambda item: self.on_region_changed(MODE_SELECT_RAYLEIGH, item))

        self.setupTables()

        self.calibration_controller = CalibrationController()

    def update_ui(self):
        self.combobox_calibration.clear()
        session = Session.get_instance()

        if not session.file:
            return

        calib_keys = session.get_calib_keys(sort_by_time=True)
        self.combobox_calibration.addItems(calib_keys)
        self.refresh_plot()

    def reset_ui(self):
        self.table_Brillouin_regions.setRowCount(0)
        self.table_Rayleigh_regions.setRowCount(0)
        self.combobox_calibration.clear()
        self.calibration_progress.setValue(0)
        self.plot.cla()
        self.mplcanvas.draw()

    def prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            self.refresh_plot()
            self.checkFrameNavigationButtons()

    def next_frame(self):
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()
        frame_count = session.get_calibration_image_count(calib_key)
        if self.current_frame < frame_count - 1:
            self.current_frame += 1
            self.refresh_plot()
            self.checkFrameNavigationButtons()

    def checkFrameNavigationButtons(self):
        if self.current_frame > 0:
            self.button_prev_frame.setEnabled(True)
        else:
            self.button_prev_frame.setEnabled(False)

        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()
        if calib_key:
            frame_count = session.get_calibration_image_count(calib_key)
            if self.current_frame < frame_count - 1:
                self.button_next_frame.setEnabled(True)
            else:
                self.button_next_frame.setEnabled(False)

    def clear_calibration(self):
        cc = CalibrationController()
        calib_key = self.combobox_calibration.currentText()
        cc.clear_calibration(calib_key)
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
        if not self.plot.lines or not self.plot.lines[0]:
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
        self.checkFrameNavigationButtons()
        self.refresh_plot()

    def calibrate(self):
        calib_key = self.combobox_calibration.currentText()

        count = mp.Value('I', 0, lock=True)
        max_count = mp.Value('i', 0, lock=True)

        dnkw = {
            "calib_key": calib_key,
            "count": count,
            "max_count": max_count,
        }

        self.thread.set_task(
            func=self.calibration_controller.calibrate, fkw=dnkw)
        self.thread.start()
        # Show a progress until computation is done
        while max_count.value == 0 or count.value < max_count.value:
            time.sleep(.05)
            self.calibration_progress.setValue(count.value)
            if max_count.value >= 0:
                self.calibration_progress.setMaximum(max_count.value)
            QtCore.QCoreApplication.instance().processEvents()
        # make sure the thread finishes
        self.thread.wait()

        self.refresh_plot()

    def calibrate_all(self, do_not=None):
        session = Session.get_instance()
        calib_keys = session.get_calib_keys(sort_by_time=True)

        if not calib_keys:
            return

        self.calibration_progress.setMaximum(len(calib_keys))

        for i, calib_key in enumerate(calib_keys):
            self.combobox_calibration.setCurrentText(calib_key)

            dnkw = {
                "calib_key": calib_key,
            }

            if do_not != 'find_peaks':
                self.thread.set_task(
                    func=self.calibration_controller.find_peaks, fkw=dnkw)
                self.thread.start()
                self.thread.wait()
            if do_not != 'calibrate':
                self.thread.set_task(
                    func=self.calibration_controller.calibrate, fkw=dnkw)
                self.thread.start()
                self.thread.wait()
            self.calibration_progress.setValue(i + 1)

            self.refresh_plot()
            QtCore.QCoreApplication.instance().processEvents()

    def refresh_plot(self):
        self.plot.cla()
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()
        if not calib_key:
            return

        try:
            cc = CalibrationController()
            spectrum, _, _ = cc.extract_spectra(
                calib_key,
                frame_num=self.current_frame
            )
            if spectrum is None:
                return

            cm = session.calibration_model()
            if not cm:
                return

            if len(spectrum) > 0:
                spectrum = spectrum[0]
                frequencies = cm.get_frequencies_by_calib_key(calib_key)
                frequency = None
                if frequencies:
                    frequency = 1e-9*frequencies[self.current_frame]
                    self.plot.plot(frequency, spectrum)
                    self.plot.set_xlabel('$f$ [GHz]')
                    self.plot.set_xlim(1e-9*np.min(frequencies),
                                       1e-9*np.max(frequencies))
                else:
                    self.plot.plot(spectrum)
                    self.plot.set_xlabel('$f$ [pix]')
                    self.plot.set_xlim(0, len(spectrum))
                self.plot.set_ylim(bottom=0)
                self.plot.set_title('Frame %d' %
                                    (self.current_frame+1))

                regions = cm.get_brillouin_regions(calib_key)
                table = self.table_Brillouin_regions
                self.refresh_regions(spectrum, regions, table, 'r', frequency)

                for region_key, region in enumerate(regions):
                    fit = cm.brillouin_fits\
                        .get_fit(calib_key, region_key, self.current_frame)
                    if fit is not None:
                        w0s = fit.w0s
                        w0s_f = cm.get_frequency_by_calib_key(w0s, calib_key)
                        if w0s_f is not None:
                            self.plot.vlines(1e-9*w0s_f[0], 0, np.nanmax(
                                spectrum), colors=['black'])
                            self.plot.vlines(1e-9*w0s_f[1], 0, np.nanmax(
                                spectrum), colors=['black'])
                        else:
                            self.plot.vlines(w0s[0], 0, np.nanmax(
                                spectrum), colors=['black'])
                            self.plot.vlines(w0s[1], 0, np.nanmax(
                                spectrum), colors=['black'])

                regions = cm.get_rayleigh_regions(calib_key)
                table = self.table_Rayleigh_regions
                self.refresh_regions(spectrum, regions, table, 'm', frequency)

                for region_key, region in enumerate(regions):
                    fit = cm.rayleigh_fits\
                        .get_fit(calib_key, region_key, self.current_frame)
                    if fit is not None:
                        w0 = fit.w0
                        w0_f = cm.get_frequency_by_calib_key(w0, calib_key)
                        if w0_f is not None:
                            self.plot.vlines(1e-9*w0_f, 0, np.nanmax(
                                spectrum), colors=['black'])
                        else:
                            self.plot.vlines(w0, 0, np.nanmax(
                                spectrum), colors=['black'])

                expected = cc.expected_frequencies(
                    calib_key, self.current_frame)
                if expected is not None:
                    self.plot.vlines(1e-9 * expected, 0, np.nanmax(
                        spectrum), colors=['green'])

        except Exception as e:
            logger.error('Exception occurred in calibration: %s' % e)
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

    def find_peaks(self):
        """
        Automatically finds the Rayleigh and Brillouin peaks.
        """
        calib_key = self.combobox_calibration.currentText()
        cc = CalibrationController()
        cc.find_peaks(calib_key)
        self.refresh_plot()

    def show_options(self):
        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.calibration', 'calibration_options.ui')
        self.options_dialog = QtWidgets.QDialog(
            self,
            QtCore.Qt.WindowType.WindowTitleHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        uic.loadUi(ui_file, self.options_dialog)
        self.options_dialog.setWindowTitle('Calibration options')
        self.options_dialog.setWindowModality(
            QtCore.Qt.WindowModality.ApplicationModal)
        self.options_dialog.button_ok.clicked.connect(
            self.apply_and_close_options
        )
        self.options_dialog.button_apply.clicked.connect(
            self.apply_options
        )
        self.options_dialog.button_cancel.clicked.connect(
            self.close_options
        )
        self.options_dialog.temperature.valueChanged.connect(
            self.temperature_changed
        )
        self.options_dialog.adjustSize()

        self.mplcanvas_options = MplCanvas(self.options_dialog.widget_plot,
                                           toolbar=('Home', 'Pan', 'Zoom'))
        self.plot_options =\
            self.mplcanvas_options.get_figure().add_subplot(111)

        self.update_options_view()
        self.options_dialog.exec()

    def apply_and_close_options(self):
        self.apply_options()
        self.close_options()

    def apply_options(self):
        session = Session.get_instance()
        cm = session.calibration_model()
        if cm is None:
            return

        shift_0_old = session.setup.calibration.shift_methanol
        shift_1_old = session.setup.calibration.shift_water
        shift_0_new = 1e9 * self.options_dialog.shift_0.value()
        shift_1_new = 1e9 * self.options_dialog.shift_1.value()

        if (shift_0_old != shift_0_new) | (shift_1_old != shift_1_new):
            # Set current calibration values
            session.setup.calibration.set_shift_methanol(shift_0_new)
            session.setup.calibration.set_shift_water(shift_1_new)

            # Apply new calibration values
            calib_keys = session.get_calib_keys()
            for calib_key in calib_keys:
                self.calibration_controller.calibrate(calib_key)

            self.update_options_view()
            self.refresh_plot()

    def close_options(self):
        self.options_dialog.close()

    def temperature_changed(self):
        temperature = self.sender().value()

        session = Session.get_instance()
        session.setup.set_temperature(temperature)
        self.update_options_view()

    def update_options_view(self):
        if self.options_dialog is None:
            return

        session = Session.get_instance()
        cm = session.calibration_model()
        if cm is None:
            return

        # Set current calibration values
        self.options_dialog.shift_0.setValue(
            1e-9 * session.setup.calibration.shift_methanol)
        self.options_dialog.shift_1.setValue(
            1e-9 * session.setup.calibration.shift_water)
        self.options_dialog.temperature.setValue(
            session.setup.temperature - 273.15
        )

        # Get the sorted calibration keys
        calib_keys = session.get_calib_keys(sort_by_time=True)
        if calib_keys is None:
            return

        # Allocate the shifts array
        shifts = np.empty((
            len(calib_keys)
            * session.get_calibration_image_count(calib_keys[0]),
            session.setup.calibration.num_brillouin_samples * 2
        ))
        shifts[:] = np.nan

        # Get the resulting fitted calibration frequencies
        cal_image = 0
        for calib_key in calib_keys:
            frame_count = session.get_calibration_image_count(calib_key)
            for frame in range(frame_count):
                cal_image = cal_image + 1
                w0s = cm.get_sorted_peaks(calib_key, frame)

                if w0s is None or w0s.shape[0]\
                        != session.setup.calibration.\
                        num_brillouin_samples * 2 + 2:
                    continue

                w0s_f = cm.get_frequency_by_calib_key(w0s, calib_key)

                if w0s_f is None:
                    continue

                for i in range(
                        session.setup.calibration.num_brillouin_samples):
                    shifts[cal_image - 1, i] =\
                        1e-9 * abs(w0s_f[0] - w0s_f[i + 1])
                    shifts[cal_image - 1, -1*i - 1] =\
                        1e-9 * abs(w0s_f[-1] - w0s_f[-1*i - 2])

        # Clear the calibration plot
        self.plot_options.cla()
        # Plot calibration reference frequency shifts
        self.plot_options.hlines(
            1e-9 * session.setup.calibration.shift_methanol,
            0, len(shifts) - 1, colors=['black'])
        if session.setup.calibration.num_brillouin_samples > 1:
            self.plot_options.hlines(
                1e-9 * session.setup.calibration.shift_water,
                0, len(shifts) - 1, colors=['black'])

        # Plot the fitted calibration frequency shifts
        self.plot_options.plot(shifts)

        # Set the axis labels
        self.plot_options.set_ylabel('$\\nu_\\mathrm{B}$ [GHz]')
        # Update the plot
        self.mplcanvas_options.draw()
