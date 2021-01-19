from PyQt5.QtWidgets import QWidget
from PyQt5 import QtCore

from bmicro.gui.main import BMicro


def test_main_window_can_activate_all_tabs(qtbot):

    window = BMicro()
    qtbot.add_widget(window)

    window.close()
