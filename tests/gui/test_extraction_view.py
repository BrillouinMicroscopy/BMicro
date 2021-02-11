import pathlib

import pytest

from bmicro.gui.main import BMicro


def data_file_path(file_name):
    return pathlib.Path(__file__).parent.parent / 'data' / file_name


@pytest.fixture
def window(mocker):
    window = BMicro()
    file_name = data_file_path('Water.h5')

    def mock_getOpenFileName(self, *args, **kwargs):
        return file_name, None

    mocker.patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                 mock_getOpenFileName)
    window.open_file()
    yield window
    window.close()
