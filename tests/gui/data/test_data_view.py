import pathlib

from PyQt5 import QtCore

from bmicro.gui.main import BMicro


def data_file_path(file_name):
    return pathlib.Path(__file__).parent.parent.parent / 'data' / file_name


def test_clicking_rotate_updates_session(qtbot, mocker):

    window = BMicro()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)

    window.open_file()
    assert window.session.rotation == 0
    qtbot.mouseClick(
        window.widget_data_view.radio_rotation_90_cw, QtCore.Qt.LeftButton)
    assert window.session.rotation == -90
    qtbot.mouseClick(
        window.widget_data_view.radio_rotation_90_ccw, QtCore.Qt.LeftButton)
    assert window.session.rotation == 90

    # For some reason, the following code three lines of code do not trigger
    # the event of the radio_rotation_none radio button. But
    # this happens only for Windows, not for Mac or Linux!
    # This appears to be a bug in the fixture qtbot of pytest-qt,
    # because performing the test "manually" works fine even
    # for Windows.
    #
    # qtbot.mouseClick(
    #     window.widget_data_view.radio_rotation_none, QtCore.Qt.LeftButton)
    # assert window.session.rotation == 0

    window.close()


def test_clicking_reflect_updates_session(qtbot, mocker):

    window = BMicro()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)

    window.open_file()
    assert window.session.reflection == {
        'vertically': False, 'horizontally': False}

    qtbot.mouseClick(
        window.widget_data_view.checkbox_reflect_horizontally,
        QtCore.Qt.LeftButton)
    assert window.session.reflection == {
        'vertically': False, 'horizontally': True}

    qtbot.mouseClick(
        window.widget_data_view.checkbox_reflect_vertically,
        QtCore.Qt.LeftButton)
    assert window.session.reflection == {
        'vertically': True, 'horizontally': True}

    qtbot.mouseClick(
        window.widget_data_view.checkbox_reflect_horizontally,
        QtCore.Qt.LeftButton)
    assert window.session.reflection == {
        'vertically': True, 'horizontally': False}

    window.close()


def test_open_file_shows_preview(qtbot, mocker):
    window = BMicro()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)

    window.open_file()

    assert len(window.widget_data_view.mplcanvas.fig.get_axes()) > 0

    window.close()
