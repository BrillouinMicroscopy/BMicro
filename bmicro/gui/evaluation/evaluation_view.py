import pkg_resources
import logging

from PyQt5 import QtWidgets, QtCore, uic
import multiprocessing as mp
import time

# from bmlab.session import Session

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

        self.button_evaluate.released.connect(self.evaluate)

        self.setup_parameter_selection_combobox()

        self.evaluation_controller = EvaluationController()

        self.evaluation_abort = mp.Value('I', False, lock=True)
        self.evaluation_running = False

    def setup_parameter_selection_combobox(self):
        return
        # session = Session.get_instance()
        # em = session.evaluation_model()
        #
        # if em is None:
        #     return
        #
        # parameters = em.get_parameters
        # param_labels = []
        # for parameter in parameters:
        #     param_labels.append(parameter.label + parameter.unit)
        #
        # self.combobox_parameter.addItems(param_labels)

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
        while (max_count.value == 0 or count.value < max_count.value
               and not self.evaluation_abort.value):
            time.sleep(.05)
            self.evaluation_progress.setValue(count.value)
            if max_count.value >= 0:
                self.evaluation_progress.setMaximum(max_count.value)
            self.refresh_plot()
            QtCore.QCoreApplication.instance().processEvents()
        # make sure the thread finishes
        thread.wait()

        self.evaluation_running = False
        self.button_evaluate.setText('Evaluate')

        self.refresh_plot()

    def refresh_plot(self):
        return
