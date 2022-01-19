import pathlib
from collections import namedtuple

import pytest

from bmlab.session import Session

from bmicro.gui.main import BMicro


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
    assert session.extraction_model().get_points('1') == [(50, 50), (150, 150)]
    assert session.extraction_model().get_points('2') == []

    # Change back to default mode
    ev.toggle_mode()

    # Clicking should not add point
    event = Event(111, 111)
    ev.on_click_image(event)
    assert session.extraction_model().get_points('1') == [(50, 50), (150, 150)]


def test_selecting_three_points_creates_circle_fit(qtbot, window):
    ev = window.widget_extraction_view
    # Change to select mode:
    ev.toggle_mode()
    event = Event(0, 100)
    ev.on_click_image(event)
    event = Event(100, 0)
    ev.on_click_image(event)
    session = Session.get_instance()
    assert session.extraction_model().get_circle_fit('1') is None
    event = Event(141, 141)
    ev.on_click_image(event)
    fit = session.extraction_model().get_circle_fit('1')
    center, radius = fit
    assert center
    assert radius


def test_clicking_clear_deletes_points(qtbot, window):
    ev = window.widget_extraction_view
    # Change to select mode:
    ev.toggle_mode()

    event = Event(50, 50)
    ev.on_click_image(event)

    session = Session.get_instance()
    assert session.extraction_model().get_points('1') == [(50, 50)]
    ev.clear_points()
    assert session.extraction_model().get_points('1') == []


def test_clicking_find_points_finds_points(qtbot, window):
    ev = window.widget_extraction_view
    ev.clear_points()

    session = Session.get_instance()
    assert session.extraction_model().get_points('1') == []

    ev.find_points()
    assert len(session.extraction_model().get_points('1')) > 0
