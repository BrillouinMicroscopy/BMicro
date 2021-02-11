import pathlib
from collections import namedtuple

import pytest

from bmicro.gui.main import BMicro
from bmicro.session import Session


def data_file_path(file_name):
    return pathlib.Path(__file__).parent.parent / 'data' / file_name


Event = namedtuple('Event', 'xdata ydata')


@pytest.fixture
def window(mocker):
    window = BMicro()
    Session.get_instance().clear()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)
    window.open_file()
    yield window
    window.close()


def test_clicking_in_select_mode_adds_points(qtbot, window):
    ev = window.widget_extraction_view
    # Change to select mode:
    ev.toggle_mode()

    event = Event(50, 50)
    ev.on_click_image(event)
    event = Event(150, 150)
    ev.on_click_image(event)

    session = Session.get_instance()
    assert session.extraction_model.get_points('1') == [(50, 50), (150, 150)]
    assert session.extraction_model.get_points('2') == []

    # Change back to default mode
    ev.toggle_mode()

    # Clicking should not add point
    event = Event(111, 111)
    ev.on_click_image(event)
    assert session.extraction_model.get_points('1') == [(50, 50), (150, 150)]


def test_clicking_clear_deletes_points(qtbot, window):
    ev = window.widget_extraction_view
    # Change to select mode:
    ev.toggle_mode()

    event = Event(50, 50)
    ev.on_click_image(event)

    session = Session.get_instance()
    assert session.extraction_model.get_points('1') == [(50, 50)]
    ev.clear_points()
    assert session.extraction_model.get_points('1') == []
