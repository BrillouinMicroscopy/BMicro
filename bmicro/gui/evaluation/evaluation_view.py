from importlib import resources
import logging
import numpy as np
import matplotlib
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.axes3d import Axes3D
import warnings

import time

from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal, QCoreApplication
import multiprocessing as mp

from bmlab.session import Session
from bmlab.fits import lorentz

from bmicro.gui.mpl import MplCanvas

from bmlab.controllers import EvaluationController

logger = logging.getLogger(__name__)


class Worker(QObject):
    finished = pyqtSignal()

    def __init__(self, fkw):
        super().__init__()
        self.evaluation_controller = EvaluationController()
        self.fkw = fkw

    def run(self):
        self.evaluation_controller.evaluate(**self.fkw)
        self.finished.emit()


class EvaluationView(QtWidgets.QWidget):
    """
    Class for the evaluation widget
    """

    def __init__(self, *args, **kwargs):
        super(EvaluationView, self).__init__(*args, **kwargs)

        ref = resources.files('bmicro.gui.evaluation') / 'evaluation_view.ui'
        with resources.as_file(ref) as ui_file:
            uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget,
                                   toolbar=('Home', 'Pan', 'Zoom'))
        self.mplcanvas.get_figure().canvas.mpl_connect(
            'button_press_event', self.on_click_image)
        self.plot = self.mplcanvas.get_figure().add_subplot(111)
        self.image_map = None
        self.colorbar = None

        self.image_spectrum_dialog = None
        self.isd_image_canvas = None
        self.isd_image_plot = None
        self.isd_image_map = None
        self.isd_image_colorbar = None
        self.isd_spectrum_canvas = None
        self.isd_spectrum_plot = None

        self.button_evaluate.released.connect(self.evaluate)

        self.setup_parameter_selection_combobox()

        self.combobox_parameter.currentIndexChanged.connect(
            self.on_select_parameter)
        self.combobox_peak_number.currentIndexChanged.connect(
            self.on_select_parameter)

        self.aspect_ratio.clicked.connect(
            self.refresh_plot)

        self.autoscale.clicked.connect(
            self.on_scale_changed)
        self.value_min.valueChanged.connect(
            self.on_scale_changed)
        self.value_max.valueChanged.connect(
            self.on_scale_changed)

        self.evaluation_controller = EvaluationController()

        self.evaluation_abort = mp.Value('I', False, lock=True)
        self.evaluation_running = False

        self.session = Session.get_instance()

        self.evaluation_timer = QTimer()
        self.evaluation_timer.timeout.connect(self.refresh_ui)
        self.count = None
        self.max_count = None
        self.thread = None
        self.worker = None
        # Currently used to determine if we should update the plot
        # Might not be necessary anymore once the plot is fast enough.
        self.plot_count = 0

        self.bounds_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.bounds_table.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.bounds_table.cellChanged.connect(self.boundsChanged)

        self.nrBrillouinPeaks_1.toggled.connect(
            lambda: self.setNrBrillouinPeaks(1))
        self.nrBrillouinPeaks_2.toggled.connect(
            lambda: self.setNrBrillouinPeaks(2))
        self.nrBrillouinPeaks_4.toggled.connect(
            lambda: self.setNrBrillouinPeaks(4))

    def update_ui(self):
        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            return

        if evm.nr_brillouin_peaks == 1:
            self.nrBrillouinPeaks_1.setChecked(True)
            self.bounds_table.setEnabled(False)
        elif evm.nr_brillouin_peaks == 2:
            self.nrBrillouinPeaks_2.setChecked(True)
            self.bounds_table.setEnabled(True)
        elif evm.nr_brillouin_peaks == 4:
            self.nrBrillouinPeaks_4.setChecked(True)
            self.bounds_table.setEnabled(True)

        self.updateBoundsTable()
        self.setup_parameter_selection_combobox()
        self.refresh_plot()

    def updateBoundsTable(self):
        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            self.bounds_table.setRowCount(0)
            self.bounds_table.setEnabled(False)
            return
        bounds_w0 = evm.bounds_w0
        bounds_fwhm = evm.bounds_fwhm
        if bounds_w0 is None or bounds_fwhm is None:
            self.bounds_table.setRowCount(0)
        else:
            self.bounds_table.setColumnCount(4)
            self.bounds_table.setRowCount(len(bounds_w0))
            for i, bound in enumerate(bounds_w0):
                item = QtWidgets.QTableWidgetItem(str(bound[0]))
                self.bounds_table.setItem(i, 0, item)
                item = QtWidgets.QTableWidgetItem(str(bound[1]))
                self.bounds_table.setItem(i, 1, item)
            for i, bound in enumerate(bounds_fwhm):
                item = QtWidgets.QTableWidgetItem(str(bound[0]))
                self.bounds_table.setItem(i, 2, item)
                item = QtWidgets.QTableWidgetItem(str(bound[1]))
                self.bounds_table.setItem(i, 3, item)

        self.bounds_table.setEnabled(evm.nr_brillouin_peaks > 1)

    def on_click_image(self, event):
        """
        Action triggered when user clicks Brillouin map.

        Parameters
        ----------
        event: matplotlib event object
            The mouse click event.
        """
        # If the click is outside the axes, skip it
        if event.inaxes is None:
            return
        # If we don't have a session we have not loaded data yet
        session = Session.get_instance()
        if session is None:
            return

        # Get the resolution of the measurement
        resolution = self.session.get_payload_resolution()
        if resolution is None:
            return

        # Get the positions and normalize them
        positions = list(self.session.get_payload_positions().values())
        for position in positions:
            position -= np.nanmean(position)

        # Get the indices of the dimensions to check
        idx = [idx for idx, dim in enumerate(resolution) if dim > 1]

        # Only works for 1D and 2D plots
        if len(idx) < 1 or len(idx) > 2:
            return

        # Determine the indices of the click in the positions arrays
        click_pos = (event.xdata, event.ydata)
        indices = np.zeros(len(resolution), dtype="int")
        for ind, p_ind in enumerate(idx):
            dslice = [slice(None) if p_ind == i else 0
                      for i, res in enumerate(resolution)]
            r = abs(positions[p_ind][tuple(dslice)] - click_pos[ind])
            indices[p_ind] = int(np.argmin(r))

        # Convert indices to key
        image_key = self.evaluation_controller\
            .get_key_from_indices(resolution, *indices)

        # If the modal is not open yet, open it
        self.open_image_spectrum()

        # Show position and key
        self.image_spectrum_dialog.image_spectrum_label.setText(
            "Position "
            f"x: {positions[0][tuple(indices)]:#0.1f} [µm], "
            f"y: {positions[1][tuple(indices)]:#0.1f} [µm], "
            f"z: {positions[2][tuple(indices)]:#0.1f} [µm], "
            f"image key: {image_key}"
        )

        # Get the image plot it
        image = session.get_payload_image(image_key, 0)
        if image is not None:
            if isinstance(self.isd_image_map, matplotlib.image.AxesImage):
                self.isd_image_map.set_data(image.T)
            else:
                self.isd_image_map = self.isd_image_plot.imshow(
                    image.T, origin='lower', vmin=100, vmax=300
                )
                self.isd_image_colorbar = \
                    self.isd_image_canvas\
                        .get_figure().colorbar(self.isd_image_map)
        self.isd_image_canvas.draw()

        # Get spectrum and plot it
        self.isd_spectrum_plot.cla()
        spectra = session.evaluation_model().get_spectra(image_key)
        cm = session.calibration_model()
        payload_time = session.get_payload_time(image_key)
        frequencies = cm.get_frequencies_by_time(payload_time)

        if spectra is not None and frequencies is not None:
            image_nr = 0
            spectrum = np.nanmean(spectra, image_nr)

            # Also try to get the fit
            brillouin_fits, rayleigh_fits =\
                self.evaluation_controller.get_fits(image_key)

            # Show the measured data
            self.isd_spectrum_plot.plot(1e-9 * frequencies[0],
                                        spectrum, color='tab:blue')
            self.isd_spectrum_plot.set_xlabel('$f$ [GHz]')

            pm = session.peak_selection_model()
            evm = session.evaluation_model()
            if pm is not None and evm is not None:
                # Show the Brillouin peaks
                brillouin_regions = pm.get_brillouin_regions()
                # Iterate over the regions
                for region_nr in range(brillouin_fits[0].shape[1]):
                    x = np.linspace(
                        brillouin_regions[region_nr][0],
                        brillouin_regions[region_nr][1],
                        200
                    )
                    # First entry is always a single-peak fit,
                    # the following entries belong to a multi-peak fit
                    for peak_nr in range(brillouin_fits[0].shape[2]):
                        idx = (image_nr, region_nr, peak_nr)
                        current_fit = lorentz(
                            x,
                            brillouin_fits[0][idx],
                            brillouin_fits[1][idx],
                            brillouin_fits[2][idx]
                        )
                        if peak_nr < 2:
                            y = current_fit
                        else:
                            y += current_fit
                        if peak_nr == 0:
                            color = 'tab:red'
                        else:
                            color = 'tab:orange'
                        # We plot the fit for the first and last entry
                        if peak_nr == 0 or\
                                peak_nr == (brillouin_fits[0].shape[2] - 1):
                            self.isd_spectrum_plot.plot(
                                1e-9 * x,
                                y + brillouin_fits[3][idx],
                                color=color
                            )

                # Show the Rayleigh peaks
                rayleigh_regions = pm.get_rayleigh_regions()
                # Iterate over the regions
                for region_nr in range(rayleigh_fits[0].shape[1]):
                    x = np.linspace(
                        rayleigh_regions[region_nr][0],
                        rayleigh_regions[region_nr][1],
                        200
                    )
                    idx = (image_nr, region_nr, 0)
                    y = lorentz(
                        x,
                        rayleigh_fits[0][idx],
                        rayleigh_fits[1][idx],
                        rayleigh_fits[2][idx]
                    ) + rayleigh_fits[3][idx]
                    self.isd_spectrum_plot.plot(1e-9 * x,
                                                y, color='tab:purple')

        self.isd_spectrum_canvas.draw()

    def open_image_spectrum(self):
        if self.image_spectrum_dialog is None:
            self.image_spectrum_dialog = QtWidgets.QDialog(
                self,
                QtCore.Qt.WindowType.WindowTitleHint |
                QtCore.Qt.WindowType.WindowCloseButtonHint |
                QtCore.Qt.WindowType.WindowMaximizeButtonHint |
                QtCore.Qt.WindowType.WindowMinimizeButtonHint
            )
            ref = resources.files('bmicro.gui.evaluation') / 'spectrum_view.ui'
            with resources.as_file(ref) as ui_file:
                uic.loadUi(ui_file, self.image_spectrum_dialog)
            self.image_spectrum_dialog\
                .setWindowTitle('Camera image & spectrum')
            self.image_spectrum_dialog.setWindowModality(
                QtCore.Qt.WindowModality.NonModal)

            self.image_spectrum_dialog.show()

            self.isd_image_canvas = MplCanvas(
                self.image_spectrum_dialog.image_widget,
                toolbar=('Home', 'Pan', 'Zoom'))
            self.isd_image_plot =\
                self.isd_image_canvas.get_figure().add_subplot(111)
            self.isd_image_map = None
            self.isd_image_colorbar = None

            self.isd_spectrum_canvas = MplCanvas(
                self.image_spectrum_dialog.spectrum_widget,
                toolbar=('Home', 'Pan', 'Zoom'))
            self.isd_spectrum_plot =\
                self.isd_spectrum_canvas.get_figure().add_subplot(111)

        if self.image_spectrum_dialog.isVisible() is False:
            self.image_spectrum_dialog.setVisible(True)

    def setNrBrillouinPeaks(self, nr_brillouin_peaks):
        if not self.sender().isChecked():
            return
        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            return
        evm.setNrBrillouinPeaks(nr_brillouin_peaks)
        self.combobox_peak_number.setEnabled(nr_brillouin_peaks > 1)
        self.combobox_peak_number.blockSignals(True)
        self.combobox_peak_number.clear()
        peak_number_labels = []
        if nr_brillouin_peaks == 1:
            peak_number_labels = ['Single-Peak-Fit']
        elif nr_brillouin_peaks == 2:
            peak_number_labels = [
                'Single-Peak-Fit',
                'Two-Peak-Fit - Peak 1',
                'Two-Peak-Fit - Peak 2',
                'Two-Peak-Fit - Mean',
                'Two-Peak-Fit - Weighted Mean'
            ]
        elif nr_brillouin_peaks == 4:
            peak_number_labels = [
                'Single-Peak-Fit',
                'Four-Peak-Fit - Peak 1',
                'Four-Peak-Fit - Peak 2',
                'Four-Peak-Fit - Peak 3',
                'Four-Peak-Fit - Peak 4',
                'Four-Peak-Fit - Mean',
                'Four-Peak-Fit - Weighted Mean'
            ]
        self.combobox_peak_number.addItems(peak_number_labels)
        self.combobox_peak_number.blockSignals(False)

        self.updateBoundsTable()

    def boundsChanged(self, row, column):
        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            return

        if evm.bounds_w0 is not None:
            if column < 2:
                evm.bounds_w0[row][column] =\
                    self.bounds_table.item(row, column).text()
            elif column < 4:
                evm.bounds_fwhm[row][column - 2] =\
                    self.bounds_table.item(row, column).text()

    def clear_plots(self):
        if isinstance(self.colorbar, matplotlib.colorbar.Colorbar):
            self.colorbar.remove()
            self.colorbar = None
        # Clear existing plots
        if isinstance(self.image_map, list):
            for m in self.image_map:
                m.remove()
            self.image_map = None
        if self.image_map is not None:
            self.image_map.remove()
            self.image_map = None

    def reset_ui(self):
        self.evaluation_progress.setValue(0)
        self.clear_plots()
        self.plot.cla()
        self.updateBoundsTable()
        self.nrBrillouinPeaks_1.setChecked(True)
        self.combobox_parameter.clear()
        self.combobox_peak_number.setEnabled(False)
        self.combobox_peak_number.blockSignals(True)
        self.combobox_peak_number.clear()
        self.combobox_peak_number.addItems(['Single-Peak-Fit'])
        self.combobox_peak_number.blockSignals(False)

        self.mplcanvas.draw()

        if self.image_spectrum_dialog is not None\
                and self.image_spectrum_dialog.isVisible():
            self.image_spectrum_dialog.close()

    def setup_parameter_selection_combobox(self):

        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            return

        parameters = evm.get_parameter_keys()

        param_labels = []
        for key, parameter in parameters.items():
            param_labels.append(
                parameter['label'] + ' [' + parameter['unit'] + ']'
            )

        self.combobox_parameter.blockSignals(True)
        self.combobox_parameter.clear()
        self.combobox_parameter.addItems(param_labels)
        self.combobox_parameter.blockSignals(False)

    def on_select_parameter(self):
        self.refresh_plot()

    def on_scale_changed(self):
        autoscale = self.autoscale.isChecked()
        self.value_min.setDisabled(autoscale)
        self.value_max.setDisabled(autoscale)
        self.refresh_plot()

    def evaluate(self, blocking=False):
        # If the evaluation is already running, we abort it and reset
        #  the button label
        if self.evaluation_running:
            self.evaluation_abort.value = True
            self.refresh_ui()
            return

        self.evaluation_abort.value = False
        self.evaluation_running = True
        self.button_evaluate.setText('Cancel')
        # While the evaluation is running, we
        # disable switching to multi-peak fit and adjusting bounds
        self.nrBrillouinPeaksGroup.setEnabled(False)
        self.bounds_table.setEnabled(False)
        self.evaluation_timer.start(500)

        self.plot_count = 0
        self.count = mp.Value('I', 0, lock=True)

        # We have to initialize the value correctly here,
        # otherwise the evaluation might abort immediately
        # if max_count is set only after the evaluation_timer
        # triggered for the first time
        image_keys = self.session.get_image_keys()
        self.max_count = mp.Value('i', len(image_keys), lock=True)

        dnkw = {
            "count": self.count,
            "max_count": self.max_count,
            "abort": self.evaluation_abort,
        }

        self.thread = QThread()
        self.worker = Worker(fkw=dnkw)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.refresh_ui)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        if blocking:
            while self.evaluation_running:
                QCoreApplication.instance().processEvents()
                time.sleep(0.1)

    def refresh_ui(self):
        # If evaluation is aborted by user,
        # couldn't start or is finished,
        # we stop the timer
        if self.evaluation_abort.value or\
           self.max_count.value < 0 or\
           self.count.value >= self.max_count.value:
            self.evaluation_timer.stop()
            self.evaluation_running = False
            self.button_evaluate.setText('Evaluate')
            self.nrBrillouinPeaksGroup.setEnabled(True)
            session = Session.get_instance()
            if session.evaluation_model().nr_brillouin_peaks > 1:
                self.bounds_table.setEnabled(True)
            self.refresh_plot()

        if self.max_count.value >= 0:
            self.evaluation_progress.setMaximum(self.max_count.value)
        self.evaluation_progress.setValue(self.count.value)

        # We refresh the image every thirty points to not slow down to much
        if (self.count.value - self.plot_count) > 30:
            self.plot_count = self.count.value
            self.refresh_plot()

    def refresh_plot(self):
        session = Session.get_instance()
        evm = session.evaluation_model()
        if evm is None:
            return

        parameters = evm.get_parameter_keys()

        parameter_index = self.combobox_parameter.currentIndex()
        brillouin_peak_index = self.combobox_peak_number.currentIndex()
        parameter_key = list(parameters.keys())[parameter_index]

        data, positions, dimensionality, labels =\
            self.evaluation_controller.\
            get_data(parameter_key, brillouin_peak_index)

        # Subtract the mean value of the positions,
        # so they are centered around zero
        for position in positions:
            position -= np.nanmean(position)

        # Check that we have the correct subplot type
        if dimensionality != 3\
                and isinstance(self.plot, Axes3D):
            self.mplcanvas.get_figure().delaxes(self.plot)
            self.plot = self.mplcanvas.\
                get_figure().add_subplot(111)
        if dimensionality == 3:
            self.mplcanvas.get_figure().clf()
            self.plot = self.mplcanvas.\
                get_figure().add_subplot(111, projection='3d')

        # Create the slices list
        dslice = [slice(None) if dim > 1 else 0 for dim in data.shape]
        idx = [idx for idx, dim in enumerate(data.shape) if dim > 1]

        try:
            if dimensionality == 0:
                # If this is a line plot already, just set new data
                if isinstance(self.image_map, list) and\
                        isinstance(self.image_map[0], matplotlib.lines.Line2D):
                    self.image_map[0].set_data(0, data[tuple(dslice)])
                else:
                    self.clear_plots()
                    self.image_map =\
                        self.plot.plot(0, data[tuple(dslice)], marker='x')
                self.plot.set_xlabel('')
                self.plot.set_title(parameters[parameter_key]['label'])
                ylabel = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.plot.set_ylabel(ylabel)
                self.plot.axis('auto')
                self.plot.set_ylim(
                    tuple(
                        data[tuple(dslice)] * np.array([0.99, 1.01])
                    )
                )
            if dimensionality == 1:
                # If this is a line plot already, just set new data
                if isinstance(self.image_map, list) and\
                        isinstance(self.image_map[0], matplotlib.lines.Line2D):
                    self.image_map[0].set_data(
                        positions[idx[0]][tuple(dslice)],
                        data[tuple(dslice)]
                    )
                else:
                    self.clear_plots()
                    self.image_map = self.plot.plot(
                        positions[idx[0]][tuple(dslice)],
                        data[tuple(dslice)]
                    )
                self.plot.set_title(parameters[parameter_key]['label'])
                self.plot.set_xlabel(labels[idx[0]])
                ylabel = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.plot.set_ylabel(ylabel)
                self.plot.axis('auto')
                minx = np.nanmin(positions[idx[0]][tuple(dslice)])
                maxx = np.nanmax(positions[idx[0]][tuple(dslice)])
                if minx < maxx:
                    self.plot.set_xlim(minx, maxx)
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        action='ignore',
                        message='All-NaN slice encountered'
                    )
                    (value_min, value_max) = self.get_plot_limits(data)
                    if value_min < value_max:
                        self.plot.set_ylim(
                            value_min,
                            value_max
                        )
            if dimensionality == 2:
                # We rotate the array so the x-axis is shown as the
                # horizontal axis
                image_map = data[tuple(dslice)]
                image_map = np.rot90(image_map)
                extent = np.nanmin(positions[idx[0]][tuple(dslice)]), \
                    np.nanmax(positions[idx[0]][tuple(dslice)]), \
                    np.nanmin(positions[idx[1]][tuple(dslice)]), \
                    np.nanmax(positions[idx[1]][tuple(dslice)])
                if isinstance(self.image_map, matplotlib.image.AxesImage):
                    self.image_map.set_data(image_map)
                    self.image_map.set_extent(extent)
                else:
                    self.clear_plots()
                    self.image_map = self.plot.imshow(
                        image_map, interpolation='nearest',
                        extent=extent
                    )
                    self.colorbar =\
                        self.mplcanvas.get_figure().colorbar(self.image_map)

                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        action='ignore',
                        message='All-NaN slice encountered'
                    )
                    (value_min, value_max) = self.get_plot_limits(data)
                    if value_min < value_max:
                        self.image_map.set_clim(value_min, value_max)
                        # For some reason we have to apply the color limits
                        # twice to make it work properly
                        self.image_map.set_clim(value_min, value_max)
                self.plot.set_title(parameters[parameter_key]['label'])
                self.plot.set_xlabel(labels[idx[0]])
                self.plot.set_ylabel(labels[idx[1]])
                cb_label = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.colorbar.ax.set_title(cb_label)
                if self.aspect_ratio.isChecked():
                    self.plot.axis('scaled')
                else:
                    self.plot.axis('auto')
                self.plot.set_xlim(
                    np.nanmin(positions[idx[0]][tuple(dslice)]),
                    np.nanmax(positions[idx[0]][tuple(dslice)])
                )
                self.plot.set_ylim(
                    np.nanmin(positions[idx[1]][tuple(dslice)]),
                    np.nanmax(positions[idx[1]][tuple(dslice)])
                )
            if dimensionality == 3:
                (value_min, value_max) = self.get_plot_limits(data)

                scalar_map = matplotlib.cm.ScalarMappable(
                    norm=Normalize(vmin=value_min, vmax=value_max),
                    cmap=matplotlib.cm.viridis
                )

                plots = []

                # We slice the data along the last occurrence
                # of the shortest dimension
                b = data.shape[::-1]
                axis = len(b) - np.argmin(b) - 1

                for slice_idx in range(data.shape[axis]):
                    dslice[axis] = slice_idx

                    idx_t = tuple(dslice)
                    s = self.plot.plot_surface(
                        positions[0][idx_t],
                        positions[1][idx_t],
                        positions[2][idx_t],
                        facecolors=scalar_map.to_rgba(data[idx_t]),
                        shade=False
                    )
                    plots.append(s)
                self.image_map = plots
                self.plot.set_xlabel(labels[0])
                self.plot.set_ylabel(labels[1])
                self.plot.set_zlabel(labels[2])

                self.colorbar =\
                    self.mplcanvas.get_figure().colorbar(
                        scalar_map,
                        ax=self.plot
                    )
                cb_label = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.colorbar.ax.set_title(cb_label)

            self.mplcanvas.draw()
        except Exception as e:
            self.reset_ui()
            raise e

    def get_plot_limits(self, data):
        if self.autoscale.isChecked():
            value_min = np.nanmin(data)
            value_max = np.nanmax(data)
            self.value_min.blockSignals(True)
            self.value_min.setValue(value_min)
            self.value_min.blockSignals(False)
            self.value_max.blockSignals(True)
            self.value_max.setValue(value_max)
            self.value_max.blockSignals(False)
        else:
            value_min = self.value_min.value()
            value_max = self.value_max.value()
            if value_min > value_max:
                value_min = np.nanmin(data)
                value_max = np.nanmax(data)
        if value_min < value_max:
            # Adjust the double spin box step size
            single_step = (value_max - value_min) / 15
            self.value_min.setSingleStep(single_step)
            self.value_max.setSingleStep(single_step)

        return value_min, value_max
