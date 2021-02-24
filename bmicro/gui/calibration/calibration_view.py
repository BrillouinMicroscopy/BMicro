import pkg_resources
import logging

from PyQt5 import QtWidgets, uic
from matplotlib.widgets import SpanSelector

from bmicro.session import Session
from bmicro.gui.mpl import MplCanvas


logger = logging.getLogger(__name__)

MODE_DEFAULT = 'default'
MODE_SELECT_BRILLOUIN = 'select_brillouin_peaks'
MODE_SELECT_RAYLEIGH = 'select_rayleigh_peaks'


class CalibrationView(QtWidgets.QWidget):
    """
    Class for the calibration widget
    """

    def __init__(self, *args, **kwargs):
        super(CalibrationView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.calibration', 'calibration_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget)
        self.plot = self.mplcanvas.get_figure().add_subplot(111)

        rectprops = dict(facecolor='green', alpha=0.5)
        self.span_selector = SpanSelector(
            self.plot, onselect=self.on_select_data,
            useblit=True,
            direction='horizontal', rectprops=rectprops)

        self.button_brillouin_select_done.clicked.connect(
            self.on_select_brillouin_clicked)

        self.mode = MODE_DEFAULT

        self.combobox_calibration.currentIndexChanged.connect(
            self.on_select_calibration)

    def on_select_brillouin_clicked(self):
        if self.mode == MODE_SELECT_BRILLOUIN:
            self.button_brillouin_select_done.setText('Select')
        else:
            self.mode = MODE_SELECT_BRILLOUIN
            self.button_brillouin_select_done.setText('Done')
        self.button_rayleigh_select_done.setText('Select')

    def on_select_data(self, xmin, xmax):
        if self.mode == MODE_DEFAULT:
            return
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()

        if self.mode == MODE_SELECT_BRILLOUIN:
            cal_model = session.calibration_model()
            if cal_model:
                cal_model.add_brillouin_region(calib_key, (xmin, xmax))

        self.refresh_plot()

    def on_select_calibration(self):
        self.refresh_plot()

    def update_ui(self):
        self.combobox_calibration.clear()
        session = Session.get_instance()

        if not session.file:
            return

        calib_keys = session.current_repetition().calibration.image_keys()
        self.combobox_calibration.addItems(calib_keys)

    def refresh_plot(self):
        self.plot.cla()
        session = Session.get_instance()
        calib_key = self.combobox_calibration.currentText()

        try:
            em = session.extraction_model()
            if em:
                values = em.get_extracted_values(calib_key)
                if len(values) > 0:
                    phis = values[:, 0]
                    amplitudes = values[:, 1]
                    _, radius = em.get_circle_fit(calib_key)
                    arc_lenghts = radius * phis
                    arc_lenghts -= arc_lenghts[0]

                    if len(values) > 0:
                        self.plot.plot(arc_lenghts, amplitudes)
                        self.plot.set_xlabel('pixels')

            cm = session.calibration_model()
            if cm:
                regions = cm.brillouin_regions[calib_key]
                for region in regions:
                    mask = (region[0] < arc_lenghts) & (
                        arc_lenghts < region[1])
                    self.plot.plot(arc_lenghts[mask], amplitudes[mask], 'r')

        except Exception as e:
            logger.error('Exception occured: %s' % e)
        finally:
            self.mplcanvas.draw()
