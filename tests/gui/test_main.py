from PyQt5.QtWidgets import QWidget
from PyQt5 import QtCore

from bmicro.gui.main import BMicro


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





