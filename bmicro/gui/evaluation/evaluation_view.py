import pkg_resources
import logging
import numpy as np

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTimer
import multiprocessing as mp

from bmlab.session import Session

from bmicro.BGThread import BGThread
from bmicro.gui.mpl import MplCanvas

from bmlab.controllers.evaluation_controller import EvaluationController

logger = logging.getLogger(__name__)


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

        self.button_evaluate.released.connect(self.evaluate)

        self.parameters = {
            'brillouin_shift_f': {          # [GHz] Brillouin frequency shift
                'unit': 'GHz',
                'symbol': r'$\nu_\mathrm{B}$',
                'label': 'Brillouin frequency shift',
            },
            'brillouin_shift': {            # [pix] Brillouin frequency shift
                'unit': 'pix',
                'symbol': r'$\nu_\mathrm{B}$',
                'label': 'Brillouin frequency shift'
            },
            'brillouin_peak_fwhm_f': {      # [GHz] Brillouin peak FWHM
                'unit': 'GHz',
                'symbol': r'$\Delta_\mathrm{B}$',
                'label': 'Brillouin peak width',
            },
            'brillouin_peak_fwhm': {        # [pix] Brillouin peak FWHM
                'unit': 'pix',
                'symbol': r'$\Delta_\mathrm{B}$',
                'label': 'Brillouin peak width',
            },
            'brillouin_peak_position': {    # [pix] Brillouin peak position
                'unit': 'pix',
                'symbol': r'$s_\mathrm{B}$',
                'label': 'Brillouin peak position',
            },
            'brillouin_peak_intensity': {   # [a.u.] Brillouin peak intensity
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{B}$',
                'label': 'Brillouin peak intensity',
            },
            'rayleigh_peak_fwhm_f': {       # [GHz] Rayleigh peak FWHM
                'unit': 'GHz',
                'symbol': r'$\Delta_\mathrm{R}$',
                'label': 'Rayleigh peak width'
            },
            'rayleigh_peak_fwhm': {         # [pix] Rayleigh peak FWHM
                'unit': 'pix',
                'symbol': r'$\Delta_\mathrm{R}$',
                'label': 'Rayleigh peak width'
            },
            'rayleigh_peak_position': {     # [pix] Rayleigh peak position
                'unit': 'pix',
                'symbol': r'$s_\mathrm{R}$',
                'label': 'Rayleigh peak position'
            },
            'rayleigh_peak_intensity': {    # [a.u.] Rayleigh peak intensity
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{R}$',
                'label': 'Rayleigh peak intensity'
            },
            'intensity': {                  # [a.u.] Overall intensity of image
                'unit': 'a.u.',
                'symbol': r'$I_\mathrm{total}$',
                'label': 'Intensity'
            },
            'time': {                       # [s] The time the measurement
                'unit': 's',                # point was taken at
                'symbol': r'$t$',
                'label': 'Time'
            },
        }

        self.setup_parameter_selection_combobox()

        self.combobox_parameter.currentIndexChanged.connect(
            self.on_select_parameter)

        self.evaluation_controller = EvaluationController()

        self.evaluation_abort = mp.Value('I', False, lock=True)
        self.evaluation_running = False

        self.evaluation_timer = QTimer()
        self.evaluation_timer.timeout.connect(self.refresh_ui)
        self.count = None
        self.max_count = None
        self.thread = None
        # Currently used to determine if we should update the plot
        # Might not be necessary anymore once the plot is fast enough.
        self.plot_count = 0

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
            self.evaluation_timer.stop()
            self.evaluation_abort.value = True
            self.evaluation_running = False
            self.button_evaluate.setText('Evaluate')
            return

        self.evaluation_abort.value = False
        self.evaluation_running = True
        self.button_evaluate.setText('Cancel')
        self.evaluation_timer.start(200)

        self.plot_count = 0
        self.count = mp.Value('I', 0, lock=True)
        self.max_count = mp.Value('i', 0, lock=True)

        dnkw = {
            "count": self.count,
            "max_count": self.max_count,
            "abort": self.evaluation_abort,
        }

        self.thread = BGThread(
            func=self.evaluation_controller.evaluate, fkw=dnkw
        )
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
        # Average all non spatial dimensions
        try:
            data = np.nanmean(data, axis=tuple(range(2, data.ndim)))

            if self.image_map is None:
                self.image_map = self.plot.imshow(
                    data, interpolation='nearest'
                )
            else:
                self.image_map.set_data(data)
            self.image_map.set_clim(np.nanmin(data), np.nanmax(data))
            self.plot.set_title(self.parameters[parameter_key]['label'])
            self.mplcanvas.draw()
        except Exception:
            pass
