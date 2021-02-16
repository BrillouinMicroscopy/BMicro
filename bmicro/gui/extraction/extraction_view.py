import pkg_resources

from PyQt5 import QtWidgets, uic
from matplotlib.patches import Circle

from bmlab.image import set_orientation, find_max_in_radius

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
        self.button_clear.clicked.connect(self.clear_points)
        self.button_optimize.clicked.connect(self.optimize_points)

        self.update_ui()

    def update_ui(self):
        session = Session.get_instance()
        if not session.current_repetition():
            # TODO: Clear tab in this case
            return

        calib_keys = session.current_repetition().calibration.image_keys()
        self.combobox_datasets.clear()
        self.combobox_datasets.addItems(calib_keys)

    def on_select_dataset(self):
        self.refresh_image_plot()

    def on_click_image(self, event):
        if self.mode != MODE_SELECT:
            return
        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        # Warning: x-axis in imshow is 1-axis in img, y-axis is 0-axis
        session.extraction_model().add_point(calib_key, event.ydata,
                                             event.xdata)
        self.refresh_image_plot()

    def refresh_image_plot(self):
        self.image_plot.cla()
        session = Session.get_instance()
        image_key = self.combobox_datasets.currentText()
        if not image_key:
            return

        img = self._get_image_data()
        self.image_plot.imshow(img, origin='lower', vmin=100, vmax=300)

        points = session.extraction_model().get_points(image_key)
        for p in points:
            # Warning: x-axis in imshow is 1-axis in img, y-axis is 0-axis
            p_xy = p[1], p[0]
            circle = Circle(p_xy, radius=3, color='red')
            self.image_plot.add_patch(circle)
        self.mplcanvas.draw()

    def _get_image_data(self):
        image_key = self.combobox_datasets.currentText()
        if not image_key:
            return

        session = Session.get_instance()

        img = session.current_repetition().calibration.get_image(image_key)
        img = img[0, ...]

        img = set_orientation(img, session.orientation.rotation,
                              session.orientation.reflection['vertically'],
                              session.orientation.reflection['horizontally'])

        return img

    def toggle_mode(self):
        if self.mode == MODE_DEFAULT:
            self.mode = MODE_SELECT
            self.button_select_done.setText('Done')
        else:
            self.mode = MODE_DEFAULT
            self.button_select_done.setText('Select')

    def clear_points(self):
        calib_key = self.combobox_datasets.currentText()
        session = Session.get_instance()
        session.extraction_model().clear_points(calib_key)
        self.refresh_image_plot()

    def optimize_points(self):
        calib_key = self.combobox_datasets.currentText()
        session = Session.get_instance()
        model = session.extraction_model()
        points = model.get_points(calib_key)
        model.clear_points(calib_key)

        img = self._get_image_data()

        for p in points:
            new_point = find_max_in_radius(img, p, 20)
            # Warning: x-axis in imshow is 1-axis in img, y-axis is 0-axis
            model.add_point(
                calib_key, new_point[0], new_point[1])

        self.refresh_image_plot()
