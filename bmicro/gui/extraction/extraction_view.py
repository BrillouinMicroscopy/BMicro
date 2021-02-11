import pkg_resources

from PyQt5 import QtWidgets, uic
from matplotlib.patches import Circle

from bmlab.image_operations import set_orientation

from bmicro.session import Session
from bmicro.gui.mpl import MplCanvas


MODE_DEFAULT = 0
MODE_SELECT = 1


class ExtractionView(QtWidgets.QWidget):
    """
    Class for the extraction widget
    """

    def __init__(self, *args, **kwargs):
        super(ExtractionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.extraction', 'extraction_view.ui')
        uic.loadUi(ui_file, self)

        self.mode = MODE_DEFAULT

        self.mplcanvas = MplCanvas(self.image_widget)
        self.image_plot = self.mplcanvas.get_figure().add_subplot(111)
        self.image_plot.axis('off')
        self.mplcanvas.get_figure().canvas.mpl_connect(
            'button_press_event', self.on_click_image)

        self.combobox_datasets.currentIndexChanged.connect(
            self.on_select_dataset)

        self.button_select_done.clicked.connect(self.toggle_mode)

        self.update_ui()

    def update_ui(self):
        session = Session.get_instance()
        if not session.selected_repetition:
            # TODO: Clear tab in this case
            return

        calib_keys = session.selected_repetition.calibration.image_keys()
        self.combobox_datasets.clear()
        self.combobox_datasets.addItems(calib_keys)

    def on_select_dataset(self):
        self.refresh_image_plot()

    def on_click_image(self, event):
        if self.mode != MODE_SELECT:
            return
        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        session.extraction_model.add_point(calib_key, event.xdata, event.ydata)
        self.refresh_image_plot()

    def refresh_image_plot(self):
        self.image_plot.cla()
        image_key = self.combobox_datasets.currentText()
        if not image_key:
            return

        session = Session.get_instance()

        img = session.selected_repetition.calibration.get_image(image_key)
        img = img[0, ...]

        img = set_orientation(img, session.rotation,
                              session.reflection['vertically'],
                              session.reflection['horizontally'])

        self.image_plot.imshow(img, origin='lower')

        points = session.extraction_model.get_points(image_key)
        for p in points:
            circle = Circle(p, radius=3, color='red')
            self.image_plot.add_patch(circle)
        self.mplcanvas.draw()

    def toggle_mode(self):
        if self.mode == MODE_DEFAULT:
            self.mode = MODE_SELECT
            self.button_select_done.setText('Done')
        else:
            self.mode = MODE_DEFAULT
            self.button_select_done.setText('Select')
