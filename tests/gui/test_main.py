import pathlib

from PyQt5.QtWidgets import QWidget
from PyQt5 import QtCore

from bmicro.gui.main import BMicro


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
        qtbot.mouseClick(current_tab, QtCore.Qt.LeftButton)
        assert window.tabWidget.tabText(idx) == tab_text

    window.close()


def test_open_file_shows_metadata(qtbot, mocker):
    window = BMicro()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)

    window.open_file()
    w = window.widget_data_view
    assert w.label_selected_file.text() == str(file_name)
    assert w.label_date.text() == '2020-11-03 15:20'
    assert w.label_resolution_x.text() == '10'
    assert w.label_resolution_y.text() == '1'
    assert w.label_resolution_z.text() == '1'
    assert w.label_calibration.text() == 'True'
    assert w.textedit_comment.toPlainText() == 'Brillouin data'

    window.close()


def test_open_invalid_file_clears_session(qtbot, mocker):

    #
    # Arrange
    #
    window = BMicro()

    def mock_getOpenFileName_valid(self, *args, **kwargs):
        return data_file_path('Water.h5'), None

    def mock_getOpenFileName_invalid(self, *args, **kwargs):
        return data_file_path('nixWater.h5'), None

    #
    # Act
    #
    # Open a valid file.
    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName_valid)
    window.open_file()

    # For a valid file, metadata should show up.
    w = window.widget_data_view
    assert w.label_selected_file.text()

    # Now load an invalid file. Session should be cleared. No metadata
    # shown.
    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName_invalid)
    window.open_file()

    #
    # Assert
    #
    assert window.session.file is None
    assert w.label_selected_file.text() == ''
    assert w.label_date.text() == ''
    assert w.label_resolution_x.text() == ''
    assert w.label_resolution_y.text() == ''
    assert w.label_resolution_z.text() == ''
    assert w.label_calibration.text() == ''
    assert w.textedit_comment.toPlainText() == ''

    window.close()
