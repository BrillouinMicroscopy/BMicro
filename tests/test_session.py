import pathlib

import pytest

from bmicro.session import Session

def data_file_path(file_name):
    return pathlib.Path(__file__).parent / 'data' / file_name


def test_session_is_singleton():
    session = Session.get_instance()

    with pytest.raises(Exception):
        Session()

    assert session

    id_session = id(session)

    session = Session.get_instance()
    assert id(session) == id_session


def test_session_initializes():
    session = Session.get_instance()
    session.set_file(data_file_path('Water.h5'))

    assert len(session.extraction_models) == 1
    assert len(session.calibration_models) == 1
    assert '0' in session.calibration_models.keys()
    

def test_clear_session():
    # Arrange; set up session
    session = Session.get_instance()
    session.set_file(data_file_path('Water.h5'))
    session.orientation.rotation = 1
    session.set_current_repetition('0')

    # Act
    session.clear()

    # Assert
    assert session.file is None
    assert session.orientation.rotation == 0
    assert session.current_repetition() is None

