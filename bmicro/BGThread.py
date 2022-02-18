from PyQt6 import QtCore


class BGThread(QtCore.QThread):
    def __init__(self, func, fkw, *args, **kwargs):
        super(BGThread, self).__init__(*args, **kwargs)
        self.func = func
        self.fkw = fkw

    def run(self):
        self.result = self.func(**self.fkw)
