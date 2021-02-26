import pkg_resources
import logging

from PyQt5 import QtWidgets, uic
from matplotlib.patches import Circle as MPLCircle

import matplotlib
import numpy as np

from bmlab.geometry import Circle, discretize_arc
from bmlab.image import extract_values_along_arc

from bmicro.session import Session
from bmicro.gui.mpl import MplCanvas


MODE_DEFAULT = 0
MODE_SELECT = 1

logger = logging.getLogger(__name__)


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

        self.mplcanvas = MplCanvas(
            self.image_widget, toolbar=('Home', 'Pan', 'Zoom'))
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
        self.combobox_datasets.clear()
        if not session.current_repetition():
            return

        calib_keys = session.current_repetition().calibration.image_keys()
        self.combobox_datasets.addItems(calib_keys)

    def on_select_dataset(self):
        """
        Action triggered when user selects a calibration dataset.
        """
        self.refresh_image_plot()

    def on_click_image(self, event):
        """
        Action triggered when user clicks on preview image in selection mode.

        Parameters
        ----------
        event: matplotlib event object
            The mouse click event.
        """
        if self.mode != MODE_SELECT:
            return
        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        logger.debug('Adding point (%f, %f) for calibration key %s' % (
            event.xdata, event.ydata, calib_key
        ))
        session.extraction_model().add_point(calib_key, event.xdata,
                                             event.ydata)
        self.refresh_image_plot()

    def refresh_image_plot(self):
        """
        Updates the plot of the selected calibration image.
        """
        self.image_plot.cla()
        session = Session.get_instance()
        image_key = self.combobox_datasets.currentText()
        if not image_key:
            self.mplcanvas.draw()
            return

        img = self._get_image_data(image_key)

        # imshow should always get the transposed image such that
        # the horizontal axis of the plot coincides with the
        # 0-axis of the plotted array:
        self.image_plot.imshow(img.T, origin='lower', vmin=100, vmax=300)

        self._plot_points(session.extraction_model().get_points(image_key))

        circle_fit = session.extraction_model().get_circle_fit(image_key)

        if circle_fit:
            center, radius = circle_fit
            self.image_plot.add_patch(
                MPLCircle(center, radius, color='yellow', fill=False))
            circle = Circle(center, radius)
            phis = discretize_arc(circle, img.shape, num_points=500)

            width = 2
            length = 7

            self._plot_extraction_patches(circle, phis, length, width)

            # Extracting the values is the most time consuming part on
            # this tab.
            values = self._extract_values(
                image_key, circle, phis, length, width)
            session.extraction_model().set_extracted_values(
                image_key, phis, values)

        self.mplcanvas.draw()

    def _plot_extraction_patches(self, circle, phis, length, width):
        for phi in phis:
            p = circle.point(phi)
            diag = np.array([width, length])
            llc = p - diag / 2.
            rect = matplotlib.patches.Rectangle(
                llc, width, length, color='Yellow', fill=False)
            rotate = matplotlib.transforms.Affine2D(
            ).rotate_around(p[0], p[1], phi + np.pi / 2.)
            rect.set_transform(rotate + self.image_plot.transData)
            self.image_plot.add_patch(rect)

    def _extract_values(self, calib_key, circle, phis, length, width):

        session = Session.get_instance()
        images = session.current_repetition().calibration.get_image(calib_key)

        return extract_values_along_arc(images, session.orientation, phis,
                                        circle, length, width)

    def _plot_points(self, points):
        for p in points:
            circle = MPLCircle(p, radius=3, color='red')
            self.image_plot.add_patch(circle)

    def _get_image_data(self, calib_key, index=0):

        session = Session.get_instance()

        img = session.current_repetition().calibration.get_image(calib_key)
        img = img[index, ...]

        return session.orientation.apply(img)

    def toggle_mode(self):
        """
        Toggles between normal and selection mode.

        In selection mode, the user can select points in the calibration
        image.
        """
        if self.mode == MODE_DEFAULT:
            self.mode = MODE_SELECT
            self.button_select_done.setText('Done')
        else:
            self.mode = MODE_DEFAULT
            self.button_select_done.setText('Select')

    def clear_points(self):
        """
        Deletes the selected point for the current calibration image
        """
        calib_key = self.combobox_datasets.currentText()
        session = Session.get_instance()
        session.extraction_model().clear_points(calib_key)
        self.refresh_image_plot()

    def optimize_points(self):
        """
        Moves the selected points in the calibration image to the nearest
        maximum values.
        """
        calib_key = self.combobox_datasets.currentText()
        session = Session.get_instance()
        img = self._get_image_data(calib_key)
        session.extraction_model().optimize_points(calib_key, img)
        self.refresh_image_plot()
