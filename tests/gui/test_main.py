import pathlib
import os

from PyQt6.QtWidgets import QWidget
from PyQt6 import QtCore

from bmlab.session import Session

from bmicro.gui.main import BMicro, check_event_mime_data


def data_file_path(file_name):
    return pathlib.Path(__file__).parent.parent / 'data' / file_name


def test_main_window_can_activate_all_tabs(qtbot):

    window = BMicro()
    qtbot.add_widget(window)
    tab_texts = ['Data', 'Extraction', 'Calibration',
                 'Peak Selection', 'Evaluation']
    tab_names = ['tab_data', 'tab_extraction', 'tab_calibration',
                 'tab_peak_selection', 'tab_evaluation']

    for idx, (tab_text, tab_name) in enumerate(zip(tab_texts, tab_names)):
        current_tab = window.tabWidget.findChild(QWidget, tab_name)
        assert current_tab
        qtbot.mouseClick(current_tab, QtCore.Qt.MouseButton.LeftButton)
        assert window.tabWidget.tabText(idx) == tab_text

    window.close()


def test_open_file_shows_metadata(qtbot, mocker):
    window = BMicro()
    file_name = 'Water.h5'
    file_path = data_file_path(file_name)

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_path, None

    mocker.patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)

    window.open_file()
    w = window.widget_data_view
    assert w.label_selected_file.text() == str(file_name)
    assert w.label_selected_file.toolTip() == str(file_path)
    assert w.label_date.text() == '2020-11-03 15:20'
    assert w.label_resolution_x.text() == '10'
    assert w.label_resolution_y.text() == '1'
    assert w.label_resolution_z.text() == '1'
    assert w.label_calibration.text() == 'True'
    assert w.textedit_comment.toPlainText() == 'Brillouin data'

    window.close()


def test_check_event_mime_data():
    class DummyEvent:
        def __init__(self, *args, **kwargs):
            self.__mimeData = QtCore.QMimeData()

        def mimeData(self):
            return self.__mimeData

    event = DummyEvent()

    """ Test for empty url """
    path = check_event_mime_data(event)
    assert path is False

    """ Test for wrong file type """
    event.mimeData().setUrls([QtCore.QUrl("file:/directory/file.txt")])
    path = check_event_mime_data(event)
    assert path is False

    """ Test for correct file type """
    event.mimeData().setUrls([QtCore.QUrl("file:/directory/file.h5")])
    path = check_event_mime_data(event)
    assert path == '/directory/file.h5'


def test_save_and_load_session():
    if os.path.exists(data_file_path('Water.session.h5')):
        os.remove(data_file_path('Water.session.h5'))
    session = Session.get_instance()
    session.set_file(data_file_path('Water.h5'))
    session.set_reflection(vertically=True)
    session.extraction_models['0'].add_point('0', 10, 30, 30)
    session.save()

    assert os.path.exists(data_file_path('Water.session.h5'))

    session.clear()

    assert session.file is None
    assert session.extraction_models == {}

    session.set_file(data_file_path('Water.h5'))

    assert session.file is not None
    assert len(session.extraction_models) == 1

    os.remove(data_file_path('Water.session.h5'))
