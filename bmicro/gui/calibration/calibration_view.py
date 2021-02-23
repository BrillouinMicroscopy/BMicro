import pkg_resources

from PyQt5 import QtWidgets, uic

from bmicro.session import Session
from bmicro.gui.mpl import MplCanvas


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

        self.combobox_calibration.currentIndexChanged.connect(
            self.on_select_calibration)

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

        self.mplcanvas.draw()
