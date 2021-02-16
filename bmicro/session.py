from bmlab.file import BrillouinFile

from bmicro.model import ExtractionModel, Orientation


class Session(object):
    """
    Session stores information about the current file
    to be processed.

    Session is a singleton. It can be accessed by
    calling the get_instance() method.
    """

    __instance = None

    def __init__(self):
        """
        Constructor of Session class. Since Session is a singleton,
        users should not call it but instead use the get_instance
        method.
        """
        if Session.__instance is not None:
            raise Exception('Session is a singleton!')
        else:
            Session.__instance = self

        # Global session data:
        self.file = None
        self.orientation = Orientation()
        self.setup = None

        # Session data by repetition:
        self.extraction_models = {}

        self._current_repetition_key = None

    def current_repetition(self):
        """ Returns the repetition currently selected in data tab """
        if self.file and self._current_repetition_key:
            return self.file.get_repetition(self._current_repetition_key)
        return None

    def set_current_repetition(self, rep_key):
        self._current_repetition_key = rep_key

    def extraction_model(self):
        """
        Returns ExtractionModel instance for currently selected repetition
        """
        return self.extraction_models.get(self._current_repetition_key)

    @staticmethod
    def get_instance():
        """
        Returns the singleton instance of Session

        Returns
        -------
        out: Session
        """
        if Session.__instance is None:
            Session()
        return Session.__instance

    def set_file(self, file_name):
        """
        Set the file to be processed.

        Loads the corresponding data from HDF file.

        Parameters
        ----------
        file_name : str
            The file name.

        """
        try:
            self.file = BrillouinFile(file_name)

            self.extraction_models = {key: ExtractionModel()
                                      for key in self.file.repetition_keys()}
        except Exception as e:
            self.file = None
            raise e

    def clear(self):
        """
        Close connection to loaded file.
        """
        Session.__instance = None

    def set_setup(self, setup):
        self.setup = setup
