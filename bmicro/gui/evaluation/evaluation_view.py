import pkg_resources
import logging
import numpy as np
import matplotlib
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.axes3d import Axes3D
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
        self.setup_parameter_selection_combobox()
        self.refresh_plot()

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

        self.mplcanvas.draw()

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

        parameters = evm.get_parameter_keys()

        parameter_index = self.combobox_parameter.currentIndex()
        parameter_key = list(parameters.keys())[parameter_index]

        data, positions, dimensionality, labels =\
            self.evaluation_controller.get_data(parameter_key)

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
                self.plot.set_xlim(
                    np.nanmin(positions[idx[0]][tuple(dslice)]),
                    np.nanmax(positions[idx[0]][tuple(dslice)])
                )
                self.plot.set_ylim(
                    np.nanmin(data),
                    np.nanmax(data)
                )
            if dimensionality == 2:
                # We rotate the array so the x axis is shown as the
                # horizontal axis
                image_map = data[tuple(dslice)]
                image_map = np.rot90(image_map)
                extent = np.nanmin(positions[idx[0]][tuple(dslice)]),\
                    np.nanmax(positions[idx[0]][tuple(dslice)]),\
                    np.nanmin(positions[idx[1]][tuple(dslice)]),\
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
                    value_min = np.nanmin(data[tuple(dslice)])
                    value_max = np.nanmax(data[tuple(dslice)])
                    if value_min < value_max:
                        self.image_map.set_clim(value_min, value_max)
                self.plot.set_title(parameters[parameter_key]['label'])
                self.plot.set_xlabel(labels[idx[0]])
                self.plot.set_ylabel(labels[idx[1]])
                cb_label = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.colorbar.ax.set_title(cb_label)
                self.plot.axis('scaled')
                self.plot.set_xlim(
                    np.nanmin(positions[idx[0]][tuple(dslice)]),
                    np.nanmax(positions[idx[0]][tuple(dslice)])
                )
                self.plot.set_ylim(
                    np.nanmin(positions[idx[1]][tuple(dslice)]),
                    np.nanmax(positions[idx[1]][tuple(dslice)])
                )
            if dimensionality == 3:
                scalar_map = matplotlib.cm.ScalarMappable(
                    norm=Normalize(vmin=np.nanmin(data), vmax=np.nanmax(data)),
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
                    self.mplcanvas.get_figure().colorbar(scalar_map)
                cb_label = parameters[parameter_key]['symbol'] +\
                    ' [' + parameters[parameter_key]['unit'] + ']'
                self.colorbar.ax.set_title(cb_label)

            self.mplcanvas.draw()
        except Exception:
            self.reset_ui()
            pass
