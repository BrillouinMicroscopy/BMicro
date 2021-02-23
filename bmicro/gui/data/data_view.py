import pkg_resources

from PyQt5 import uic, QtWidgets
import matplotlib

from bmlab.image import set_orientation

from bmicro.gui.mpl import MplCanvas
from bmicro.session import Session
from bmicro.model import AVAILABLE_SETUPS

import os

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

        self.radio_rotation_none.clicked.connect(self.on_rotation_clicked)
        self.radio_rotation_90_cw.clicked.connect(self.on_rotation_clicked)
        self.radio_rotation_90_ccw.clicked.connect(self.on_rotation_clicked)

        self.checkbox_reflect_vertically.toggled.connect(
            self.on_reflection_clicked)
        self.checkbox_reflect_horizontally.toggled.connect(
            self.on_reflection_clicked)

        self.comboBox_repetition.currentIndexChanged.connect(
            self.on_select_repetition)

        self.combobox_setup.addItems([s.name for s in AVAILABLE_SETUPS])
        self.combobox_setup.currentIndexChanged.connect(
            self.on_select_setup)

        self.update_ui()

    def update_ui(self):
        """
        When a new file is selected, update the UI accordingly.
        """
        self.label_selected_file.setText('')
        self.label_selected_file.setToolTip('')
        self.comboBox_repetition.clear()
        self.label_date.setText('')
        self.label_resolution_x.setText('')
        self.label_resolution_y.setText('')
        self.label_resolution_z.setText('')
        self.label_calibration.setText('')
        self.textedit_comment.setText('')
        self.update_preview()

        session = Session.get_instance()
        if not session.file:
            return

        filename = str(os.path.basename(session.file.path))
        self.label_selected_file.setText(filename)
        self.label_selected_file.setToolTip(str(session.file.path))
        self.label_selected_file.adjustSize()
        rep_keys = session.file.repetition_keys()
        self.comboBox_repetition.addItems(rep_keys)

        if rep_keys and self.comboBox_repetition.currentText():
            repetition = session.current_repetition()
            res = repetition.payload.resolution
            if res:
                self.label_resolution_x.setText(str(res[0]))
                self.label_resolution_y.setText(str(res[1]))
                self.label_resolution_z.setText(str(res[2]))
            date = repetition.date.strftime('%Y-%m-%d %H:%M')
            self.label_date.setText(date)
            self.textedit_comment.setText(session.file.comment)
            self.label_calibration.setText(
                str(not repetition.calibration.is_empty()))

        self.checkbox_reflect_vertically.setChecked(
            session.orientation.reflection['vertically'])
        self.checkbox_reflect_horizontally.setChecked(
            session.orientation.reflection['horizontally'])

        self.radio_rotation_none.setChecked(session.orientation.rotation == 0)
        self.radio_rotation_90_cw.setChecked(session.orientation.rotation == 3)
        self.radio_rotation_90_ccw.setChecked(
            session.orientation.rotation == 1)

    def on_rotation_clicked(self):

        radio_button = self.sender()
        if not radio_button.isChecked():
            return

        session = Session.get_instance()

        if radio_button == self.radio_rotation_none:
            session.orientation.set_rotation(0)
        elif radio_button == self.radio_rotation_90_cw:
            session.orientation.set_rotation(3)
        elif radio_button == self.radio_rotation_90_ccw:
            session.orientation.set_rotation(1)

        self.update_preview()

    def on_reflection_clicked(self):
        """ Triggered when a reflection checkbox is clicked """

        checkbox = self.sender()

        session = Session.get_instance()
        if checkbox == self.checkbox_reflect_vertically:
            session.orientation.set_reflection(vertically=checkbox.isChecked())
        elif checkbox == self.checkbox_reflect_horizontally:
            session.orientation.set_reflection(
                horizontally=checkbox.isChecked())

        self.update_preview()

    def update_preview(self):
        session = Session.get_instance()
        rep = session.current_repetition()

        if rep and rep.payload.image_keys():
            first_key = rep.payload.image_keys()[0]
            images = rep.payload.get_image(first_key)
            img = images[0, ...]

            orient = session.orientation
            img = set_orientation(img, orient.rotation,
                                  orient.reflection['vertically'],
                                  orient.reflection['horizontally'])

            self.preview.clear()

            # imshow should always get the transposed image such that
            # the horizontal axis of the plot coincides with the
            # 0-axis of the plotted array:
            self.preview.imshow(img.T, origin='lower', vmin=100, vmax=300)
            self.preview.axis('off')
            self.mplcanvas.draw()
        else:
            self.mplcanvas.get_figure().clf()
            self.preview = self.mplcanvas.get_figure().add_subplot(111)
            self.mplcanvas.draw()

    def on_select_repetition(self):
        session = Session.get_instance()
        rep_key = self.comboBox_repetition.currentText()
        session.set_current_repetition(rep_key)
        self.update_preview()

    def on_select_setup(self):
        name = self.combobox_setup.currentText()
        setup = None
        session = Session.get_instance()
        for s in AVAILABLE_SETUPS:
            if s.name == name:
                setup = s
                break
        session.setup = setup
