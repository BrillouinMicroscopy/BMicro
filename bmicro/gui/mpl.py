from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent, width=5, height=5, dpi=100):

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self)
        parent.setLayout(layout)

    def get_figure(self):
        return self.fig
