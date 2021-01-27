from bmlab.file import BrillouinFile


class Session(object):

    __instance = None

    def __init__(self):
        if Session.__instance is not None:
            raise Exception('Session is a singleton!')
        else:
            Session.__instance = self

        self.file = None

    @staticmethod
    def get_instance():
        if Session.__instance is None:
            Session()
        return Session.__instance

    def set_file(self, file_name):
        try:
            self.file = BrillouinFile(file_name)
        except Exception:
            self.file = None

    def clear(self):
        self.file = None
