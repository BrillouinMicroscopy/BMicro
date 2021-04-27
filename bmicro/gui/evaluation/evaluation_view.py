import pkg_resources
import logging
import numpy as np

from PyQt5 import QtWidgets, QtCore, uic
import multiprocessing as mp
import time

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
            self.evaluation_running = False
            self.button_evaluate.setText('Evaluate')
            return

        self.evaluation_abort.value = False
        self.evaluation_running = True
        self.button_evaluate.setText('Cancel')

        count = mp.Value('I', 0, lock=True)
        max_count = mp.Value('i', 0, lock=True)

        dnkw = {
            "count": count,
            "max_count": max_count,
            "abort": self.evaluation_abort,
        }

        thread = BGThread(func=self.evaluation_controller.evaluate, fkw=dnkw)
        thread.start()
        # Show a progress until computation is done
        plot_count = 0
        while (max_count.value == 0 or count.value < max_count.value
               and not self.evaluation_abort.value):
            time.sleep(.25)
            self.evaluation_progress.setValue(count.value)
            if max_count.value >= 0:
                self.evaluation_progress.setMaximum(max_count.value)
            # We refresh the image every twenty points to not slow down to much
            if (count.value - plot_count) > 30:
                plot_count = count.value
                self.refresh_plot()
            QtCore.QCoreApplication.instance().processEvents()
        # make sure the thread finishes
        thread.wait()

        self.evaluation_running = False
        self.button_evaluate.setText('Evaluate')

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
            self.mplcanvas.draw()
        except Exception:
            pass
