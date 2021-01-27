import pkg_resources

from PyQt5 import QtWidgets, uic

from bmicro.session import Session


class DataView(QtWidgets.QWidget):
    """
    Class for the data widget
    """

    def __init__(self, *args, **kwargs):
        super(DataView, self).__init__(*args, **kwargs)

        ui_file = pkg_resources.resource_filename(
            'bmicro.gui.data', 'data_view.ui')
        uic.loadUi(ui_file, self)

        self.session = Session.get_instance()
        self.update_ui()

    def update_ui(self):
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
