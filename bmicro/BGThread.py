from PyQt6 import QtCore


class BGThread(QtCore.QThread):
    def __init__(self, func=None, fkw=None, *args, **kwargs):
        super(BGThread, self).__init__(*args, **kwargs)
        self.func = func
        self.fkw = fkw
        self.result = None

    def set_task(self, func, fkw):
        self.func = func
        self.fkw = fkw

    def run(self):
        if self.func:
            self.result = self.func(**self.fkw)
