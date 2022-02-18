import pkg_resources
import logging
import numpy as np
import matplotlib
import warnings

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal
import multiprocessing as mp

from bmlab.session import Session

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

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.evaluation', 'evaluation_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget,
                                   toolbar=('Home', 'Pan', 'Zoom'))
        self.plot = self.mplcanvas.get_figure().add_subplot(111)
        self.image_map = None
        self.colorbar = None

        self.button_evaluate.released.connect(self.evaluate)

        self.parameters = {
            'brillouin_shift_f': {          # [GHz] Brillouin frequency shift
                'unit': 'GHz',
                'symbol': r'$\nu_\mathrm{B}$',
                'label': 'Brillouin frequency shift',
                'scaling': 1e-9,
            },
            'brillouin_shift': {            # [pix] Brillouin frequency shift
                'unit': 'pix',
                'symbol': r'$\nu_\mathrm{B}$',
                'label': 'Brillouin frequency shift',
                'scaling': 1,
            },
            'brillouin_peak_fwhm_f': {      # [GHz] Brillouin peak FWHM
                'unit': 'GHz',
                'symbol': r'$\Delta_\mathrm{B}$',
                'label': 'Brillouin peak width',
                'scaling': 1e-9,
            },
            'brillouin_peak_fwhm': {        # [pix] Brillouin peak FWHM
                'unit': 'pix',
                'symbol': r'$\Delta_\mathrm{B}$',
                'label': 'Brillouin peak width',
                'scaling': 1,
            },
            'brillouin_peak_position': {    # [pix] Brillouin peak position
                'unit': 'pix',
                'symbol': r'$s_\mathrm{B}$',
                'label': 'Brillouin peak position',
                'scaling': 1,
            },
            'brillouin_peak_intensity': {   # [a.u.] Brillouin peak intensity
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{B}$',
                'label': 'Brillouin peak intensity',
                'scaling': 1,
            },
            'rayleigh_peak_fwhm_f': {       # [GHz] Rayleigh peak FWHM
                'unit': 'GHz',
                'symbol': r'$\Delta_\mathrm{R}$',
                'label': 'Rayleigh peak width',
                'scaling': 1e-9,
            },
            'rayleigh_peak_fwhm': {         # [pix] Rayleigh peak FWHM
                'unit': 'pix',
                'symbol': r'$\Delta_\mathrm{R}$',
                'label': 'Rayleigh peak width',
                'scaling': 1,
            },
            'rayleigh_peak_position': {     # [pix] Rayleigh peak position
                'unit': 'pix',
                'symbol': r'$s_\mathrm{R}$',
                'label': 'Rayleigh peak position',
                'scaling': 1,
            },
            'rayleigh_peak_intensity': {    # [a.u.] Rayleigh peak intensity
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{R}$',
                'label': 'Rayleigh peak intensity',
                'scaling': 1,
            },
            'intensity': {                  # [a.u.] Overall intensity of image
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{total}$',
                'label': 'Intensity',
                'scaling': 1,
            },
            'time': {                       # [s] The time the measurement
                'unit': 's',                # point was taken at
                'symbol': r'$t$',
                'label': 'Time',
                'scaling': 1,
            },
        }

        self.setup_parameter_selection_combobox()

        self.combobox_parameter.currentIndexChanged.connect(
            self.on_select_parameter)

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

    def update_ui(self):
        self.refresh_plot()

    def reset_ui(self):
        self.evaluation_progress.setValue(0)
        self.plot.cla()
        self.image_map = None
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None

        self.mplcanvas.draw()

    def setup_parameter_selection_combobox(self):

        param_labels = []
        for key, parameter in self.parameters.items():
            param_labels.append(
                parameter['label'] + ' [' + parameter['unit'] + ']'
            )

        self.combobox_parameter.clear()
        self.combobox_parameter.addItems(param_labels)

    def on_select_parameter(self):
        self.refresh_plot()

    def evaluate(self):
        # If the evaluation is already running, we abort it and reset
        #  the button label
        if self.evaluation_running:
            self.evaluation_abort.value = True
            self.refresh_ui()
            return

        self.evaluation_abort.value = False
        self.evaluation_running = True
        self.button_evaluate.setText('Cancel')
        self.evaluation_timer.start(500)

        self.plot_count = 0
        self.count = mp.Value('I', 0, lock=True)
        self.max_count = mp.Value('i', 0, lock=True)

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

        parameter_index = self.combobox_parameter.currentIndex()
        parameter_key = list(self.parameters)[parameter_index]

        # TODO Adjust that for measurements of arbitrary orientations
        #  (currently assumes x-y-measurement)
        data = evm.results[parameter_key]

        resolution = session.current_repetition().payload.resolution
        dimensionality, ns_dimensions = self.get_dimensionality(resolution)

        try:
            # Average all non spatial dimensions and squeeze it
            # Don't show warning which occurs when a slice contains only NaNs
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    action='ignore',
                    message='Mean of empty slice'
                )
                data = np.squeeze(
                    np.nanmean(
                        data,
                        axis=tuple(range(3, data.ndim))
                    )
                )
            # Scale the date in case of GHz
            data = self.parameters[parameter_key]['scaling'] * data
            # Get the positions, subtract mean value, squeeze them
            positions = session.current_repetition().payload.positions
            for dim in {'x', 'y', 'z'}:
                positions[dim] = np.squeeze(
                    positions[dim] - np.nanmean(positions[dim])
                )
            if dimensionality == 0:
                if not isinstance(self.image_map, list):
                    self.image_map = self.plot.plot(data)
                else:
                    self.image_map[0].set_data(data)
                self.plot.set_title(self.parameters[parameter_key]['label'])
            if dimensionality == 1:
                pos = positions[ns_dimensions[0]]
                if not isinstance(self.image_map, list):
                    self.image_map = self.plot.plot(pos, data)
                else:
                    self.image_map[0].set_data(pos, data)
                self.plot.set_title(self.parameters[parameter_key]['label'])
                self.plot.set_xlabel(r'$' + ns_dimensions[0] + '$ [$\\mu$m]')
                ylabel = self.parameters[parameter_key]['symbol'] +\
                    ' [' + self.parameters[parameter_key]['unit'] + ']'
                self.plot.set_ylabel(ylabel)
                self.plot.set_xlim((np.nanmin(pos), np.nanmax(pos)))
                self.plot.set_ylim((np.nanmin(data), np.nanmax(data)))
            if dimensionality == 2:
                # We rotate the array so the x axis is shown as the
                # horizontal axis
                data = np.rot90(data)
                pos_h = positions[ns_dimensions[0]]
                pos_v = positions[ns_dimensions[1]]
                extent = np.nanmin(pos_h), np.nanmax(pos_h),\
                    np.nanmin(pos_v), np.nanmax(pos_v)
                if not isinstance(self.image_map, matplotlib.image.AxesImage):
                    self.image_map = self.plot.imshow(
                        data, interpolation='nearest',
                        extent=extent
                    )
                    self.colorbar =\
                        self.mplcanvas.get_figure().colorbar(self.image_map)
                else:
                    self.image_map.set_data(data)
                    self.image_map.set_extent(extent)

                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        action='ignore',
                        message='All-NaN slice encountered'
                    )
                    value_min = np.nanmin(data)
                    value_max = np.nanmax(data)
                    if value_min < value_max:
                        self.image_map.set_clim(value_min, value_max)
                self.plot.set_title(self.parameters[parameter_key]['label'])
                self.plot.set_xlabel(r'$' + ns_dimensions[0] + '$ [$\\mu$m]')
                self.plot.set_ylabel(r'$' + ns_dimensions[1] + '$ [$\\mu$m]')
                cb_label = self.parameters[parameter_key]['symbol'] +\
                    ' [' + self.parameters[parameter_key]['unit'] + ']'
                self.colorbar.ax.set_title(cb_label)
            if dimensionality == 3:
                return
            self.mplcanvas.draw()
        except Exception:
            pass

    @staticmethod
    def get_dimensionality(resolution):
        dimensionality = sum(np.array(resolution) > 1)
        dimension_labels = ['x', 'y', 'z']

        ns_dimensions = []
        for ind, dim in enumerate(resolution):
            if dim > 1:
                ns_dimensions.append(dimension_labels[ind])

        return dimensionality, ns_dimensions
