import pkg_resources
import logging

from PyQt5 import QtWidgets, uic

from bmlab.session import Session

from bmicro.gui.mpl import MplCanvas

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

        self.button_evaluation.clicked.connect(
            self.on_button_evaluation_clicked)

        self.setup_parameter_selection_combobox()

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

    def on_button_evaluation_clicked(self):
        # TODO Start evaluation
        return
