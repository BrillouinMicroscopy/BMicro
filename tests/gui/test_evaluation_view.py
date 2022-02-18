import pathlib

import pytest

from bmlab.session import Session

from bmicro.gui.main import BMicro


def data_file_path(file_name):
    return pathlib.Path(__file__).parent.parent / 'data' / file_name


@pytest.fixture
def window(mocker):
    window = BMicro()
    Session.get_instance().clear()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)
    window.open_file()
    yield window
    window.close()


def test_get_dimensionality(qtbot, window):
    ev = window.widget_evaluation_view

    dimensionality, labels = ev.get_dimensionality([1, 1, 1])
    assert dimensionality == 0
    assert labels == []

    dimensionality, labels = ev.get_dimensionality([41, 1, 1])
    assert dimensionality == 1
    assert labels == ['x']

    dimensionality, labels = ev.get_dimensionality([1, 41, 1])
    assert dimensionality == 1
    assert labels == ['y']

    dimensionality, labels = ev.get_dimensionality([1, 1, 41])
    assert dimensionality == 1
    assert labels == ['z']

    dimensionality, labels = ev.get_dimensionality([41, 41, 1])
    assert dimensionality == 2
    assert labels == ['x', 'y']

    dimensionality, labels = ev.get_dimensionality([41, 1, 41])
    assert dimensionality == 2
    assert labels == ['x', 'z']

    dimensionality, labels = ev.get_dimensionality([1, 41, 41])
    assert dimensionality == 2
    assert labels == ['y', 'z']

    dimensionality, labels = ev.get_dimensionality([41, 41, 41])
    assert dimensionality == 3
    assert labels == ['x', 'y', 'z']
