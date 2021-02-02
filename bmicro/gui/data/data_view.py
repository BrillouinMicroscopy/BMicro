import pkg_resources

from PyQt5 import uic, QtWidgets
import numpy as np
import matplotlib

from bmicro.gui.mpl import MplCanvas
from bmicro.session import Session

matplotlib.use('Qt5Agg')


class DataView(QtWidgets.QWidget):
    """
    Class for the data widget
    """

    def __init__(self, *args, **kwargs):
        super(DataView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.data', 'data_view.ui')
        uic.loadUi(ui_file, self)

        self.mplcanvas = MplCanvas(self.image_preview_widget)
        self.preview = self.mplcanvas.get_figure().add_subplot(111)
        self.preview.axis('off')

        self.session = Session.get_instance()

        self.radio_rotation_none.toggled.connect(self.on_rotation_clicked)
        self.radio_rotation_90_cw.toggled.connect(self.on_rotation_clicked)
        self.radio_rotation_90_ccw.toggled.connect(self.on_rotation_clicked)

        self.checkbox_reflect_vertically.toggled.connect(
            self.on_reflection_clicked)
        self.checkbox_reflect_horizontally.toggled.connect(
            self.on_reflection_clicked)

        self.update_ui()

    def update_ui(self):
        """
        When a new file is selected, update the UI accordingly.
        """
        self.label_selected_file.setText('')
        self.comboBox_repetition.clear()
        self.label_date.setText('')
        self.label_resolution_x.setText('')
        self.label_resolution_y.setText('')
        self.label_resolution_z.setText('')
        self.label_calibration.setText('')
        self.textedit_comment.setText('')

        if not self.session.file:
            return

        self.label_selected_file.setText(str(self.session.file.path))
        self.label_selected_file.adjustSize()
        rep_keys = self.session.file.repetition_keys()
        self.comboBox_repetition.addItems(rep_keys)

        if rep_keys and self.comboBox_repetition.currentText():
            repetition = self.session.file.get_repetition(
                self.comboBox_repetition.currentText())
            res = repetition.payload.resolution
            if res:
                self.label_resolution_x.setText(str(res[0]))
                self.label_resolution_y.setText(str(res[1]))
                self.label_resolution_z.setText(str(res[2]))
            date = repetition.date.strftime('%Y-%m-%d %H:%M')
            self.label_date.setText(date)
            self.textedit_comment.setText(self.session.file.comment)
            self.label_calibration.setText(
                str(not repetition.calibration.is_empty()))

    def on_rotation_clicked(self):

        radio_button = self.sender()

        if not radio_button.isChecked():
            return

        if radio_button == self.radio_rotation_none:
            self.session.set_rotation(0)
        elif radio_button == self.radio_rotation_90_cw:
            self.session.set_rotation(-90)
        elif radio_button == self.radio_rotation_90_ccw:
            self.session.set_rotation(90)

        self.update_preview()

    def on_reflection_clicked(self):

        checkbox = self.sender()

        if checkbox == self.checkbox_reflect_vertically:
            self.session.set_reflection(vertically=checkbox.isChecked())
        elif checkbox == self.checkbox_reflect_horizontally:
            self.session.set_reflection(horizontally=checkbox.isChecked())

        self.update_preview()

    def update_preview(self):
        img = np.random.rand(200, 200)
        img[50:150, 50:150] = 1
        self.preview.clear()
        self.preview.imshow(img)
        self.preview.axis('off')
        self.mplcanvas.draw()
