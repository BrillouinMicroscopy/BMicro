import pkg_resources

from PyQt5 import QtWidgets, uic

from bmlab.image_operations import set_orientation

from bmicro.session import Session
from bmicro.gui.mpl import MplCanvas


class ExtractionView(QtWidgets.QWidget):
    """
    Class for the extraction widget
    """

    def __init__(self, *args, **kwargs):
        super(ExtractionView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.extraction', 'extraction_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_widget)
        self.image_plot = self.mplcanvas.get_figure().add_subplot(111)
        self.image_plot.axis('off')

        self.combobox_datasets.currentIndexChanged.connect(
            self.on_select_dataset)

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
        self.mplcanvas.draw()
