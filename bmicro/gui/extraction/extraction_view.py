import pkg_resources
import logging

from PyQt6 import QtWidgets, QtCore, uic
from matplotlib.patches import Circle as MPLCircle

import matplotlib
import numpy as np

from bmlab.session import Session
from bmlab.controllers import ExtractionController

from bmicro.BGThread import BGThread
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
        self.current_frame = 0

        self.mplcanvas = MplCanvas(
            self.image_widget, toolbar=('Home', 'Pan', 'Zoom'))
        self.image_plot = self.mplcanvas.get_figure().add_subplot(111)
        self.image_plot.axis('off')
        self.mplcanvas.get_figure().canvas.mpl_connect(
            'button_press_event', self.on_click_image)

        self.thread = BGThread()

        self.combobox_datasets.currentIndexChanged.connect(
            self.on_select_dataset)

        self.table_selected_points.itemChanged.connect(
            lambda item: self.on_points_changed(item))

        self.setupTable()

        self.button_select_done.clicked.connect(self.toggle_mode)
        self.button_clear.clicked.connect(self.clear_points)
        self.button_optimize.clicked.connect(self.optimize_points)
        self.button_find_points.clicked.connect(self.find_points)
        self.button_find_points_all.clicked.connect(self.find_points_all)

        self.button_prev_frame.clicked.connect(self.prev_frame)
        self.button_next_frame.clicked.connect(self.next_frame)

        self.update_ui()
        self.checkFrameNavigationButtons()

        self.extraction_controller = ExtractionController()

    def update_ui(self):
        session = Session.get_instance()
        self.combobox_datasets.clear()
        if not session.current_repetition():
            return

        calib_keys = session.get_calib_keys(sort_by_time=True)
        self.combobox_datasets.addItems(calib_keys)

    def reset_ui(self):
        self.combobox_datasets.clear()
        self.table_selected_points.setRowCount(0)
        self.refresh_image_plot()

    def prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            self.refresh_image_plot()
            self.checkFrameNavigationButtons()

    def next_frame(self):
        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        frame_count = session.get_calibration_image_count(calib_key)
        if self.current_frame < frame_count - 1:
            self.current_frame += 1
            self.refresh_image_plot()
            self.checkFrameNavigationButtons()

    def checkFrameNavigationButtons(self):
        if self.current_frame > 0:
            self.button_prev_frame.setEnabled(True)
        else:
            self.button_prev_frame.setEnabled(False)

        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        if calib_key:
            frame_count = session.get_calibration_image_count(calib_key)
            if self.current_frame < frame_count - 1:
                self.button_next_frame.setEnabled(True)
            else:
                self.button_next_frame.setEnabled(False)

    def on_select_dataset(self):
        """
        Action triggered when user selects a calibration dataset.
        """
        self.checkFrameNavigationButtons()
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
        ec = ExtractionController()
        calib_key = self.combobox_datasets.currentText()
        logger.debug('Adding point (%f, %f) for calibration key %s' % (
            event.xdata, event.ydata, calib_key
        ))
        ec.add_point(calib_key,
                     (event.xdata, event.ydata))
        self.refresh_image_plot()

    def refresh_image_plot(self):
        """
        Updates the plot of the selected calibration image.
        """
        self.image_plot.cla()
        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()
        if not calib_key:
            self.mplcanvas.draw()
            return

        em = session.extraction_model()
        img = session.get_calibration_image(calib_key, self.current_frame)

        # imshow should always get the transposed image such that
        # the horizontal axis of the plot coincides with the
        # 0-axis of the plotted array:
        self.image_plot.imshow(img.T, origin='lower', vmin=100, vmax=300)
        self.image_plot.set_title('Frame %d' % (self.current_frame+1))

        points = em.get_points(calib_key)

        if len(points) >= 3:
            em.set_image_shape(img.shape)

            arcs = em.get_arc_by_calib_key(calib_key)
            for arc in arcs:
                dr = arc[-1] - arc[0]
                line = matplotlib.patches.FancyArrow(
                    *arc[0], dr[0], dr[1], head_width=0,
                    head_length=0, color='Yellow', alpha=0.5)
                self.image_plot.add_patch(line)

        self._plot_points(em.get_points(calib_key))

        self.mplcanvas.draw()
        self.refresh_points()

    def setupTable(self):
        self.table_selected_points.setColumnCount(2)
        self.table_selected_points\
            .setHorizontalHeaderLabels(["x", "y"])
        header = self.table_selected_points.horizontalHeader()
        header.setSectionResizeMode(0,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,
                                    QtWidgets.QHeaderView.ResizeMode.Stretch)

    def refresh_points(self):
        session = Session.get_instance()
        em = session.extraction_model()
        calib_key = self.combobox_datasets.currentText()
        if not calib_key:
            return
        if em:
            points = em.get_points(calib_key)
            self.table_selected_points.setRowCount(len(points))
            for rowIdx, point in enumerate(points):
                # Add regions to table
                # Block signals, so the itemChanged signal is not
                # emitted during table creation
                self.table_selected_points.blockSignals(True)
                for columnIdx, value in enumerate(point):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    self.table_selected_points.setItem(rowIdx, columnIdx, item)
                self.table_selected_points.blockSignals(False)

    def on_points_changed(self, item):
        row = item.row()
        column = item.column()
        value = float(item.text())

        session = Session.get_instance()
        calib_key = self.combobox_datasets.currentText()

        em = session.extraction_model()
        ec = ExtractionController()
        if em:
            points = em.get_points(calib_key)
            current_point = np.asarray(points[row])
            current_point[column] = value
            current_point = tuple(current_point)
            ec.set_point(calib_key, row, current_point)
            self.refresh_image_plot()

    def _plot_points(self, points):
        for p in points:
            circle = MPLCircle(p, radius=3, color='red', alpha=0.5)
            self.image_plot.add_patch(circle)

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

        if not session.extraction_model():
            return
        session.extraction_model().clear_points(calib_key)
        self.refresh_image_plot()

    def optimize_points(self):
        """
        Moves the selected points in the calibration image to the nearest
        maximum values.
        """
        calib_key = self.combobox_datasets.currentText()
        ec = ExtractionController()
        ec.optimize_points(calib_key)
        self.refresh_image_plot()

    def find_points(self):
        """
        Automatically finds the Rayleigh and Brillouin peaks of interest.
        """
        calib_key = self.combobox_datasets.currentText()
        ec = ExtractionController()
        ec.find_points(calib_key)
        self.refresh_image_plot()

    def find_points_all(self):
        """
        Automatically finds the Rayleigh and Brillouin peaks of interest
        for all calibrations existing.
        """
        session = Session.get_instance()
        calib_keys = session.get_calib_keys(sort_by_time=True)

        if not calib_keys:
            return

        for i, calib_key in enumerate(calib_keys):
            self.combobox_datasets.setCurrentText(calib_key)

            dnkw = {
                "calib_key": calib_key,
            }

            self.thread.set_task(
                func=self.extraction_controller.find_points, fkw=dnkw)
            self.thread.start()
            self.thread.wait()

            self.refresh_image_plot()
            QtCore.QCoreApplication.instance().processEvents()
