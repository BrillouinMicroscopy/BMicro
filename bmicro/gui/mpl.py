from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent, toolbar=False, width=5, height=5, dpi=100):

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)

        layout = QtWidgets.QVBoxLayout()

        if toolbar:

            class CustomToolbar(NavigationToolbar2QT):
                toolitems = [t for t in NavigationToolbar2QT.toolitems if
                             t[0] in toolbar]

            layout.addWidget(CustomToolbar(self, parent))

        layout.addWidget(self)

        parent.setLayout(layout)

    def get_figure(self):
        return self.fig
