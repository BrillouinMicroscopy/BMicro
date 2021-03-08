import pickle
import os

from bmlab.file import BrillouinFile

from bmlab.models.extraction_model import ExtractionModel
from bmlab.models.orientation import Orientation
from bmlab.models.calibration_model import CalibrationModel


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
            self.clear()

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

    def calibration_model(self):
        return self.calibration_models.get(self._current_repetition_key)

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
            file = BrillouinFile(file_name)
        except Exception as e:
            raise e

        """ Only load data if the file could be opened """
        self.file = file
        self.extraction_models = {key: ExtractionModel()
                                  for key in self.file.repetition_keys()}
        self.calibration_models = {key: CalibrationModel()
                                   for key in self.file.repetition_keys()}

    def clear(self):
        """
        Close connection to loaded file.
        """

        # Global session data:
        self.file = None
        self.orientation = Orientation()
        self.setup = None

        # Session data by repetition:
        self.extraction_models = {}

        self._current_repetition_key = None

    def set_setup(self, setup):
        self.setup = setup

    def save(self):
        if self.file is None:
            return
        h5_file_name = str(self.file.path)
        bms_file_name = h5_file_name[:-3] + '.bms'

        with open(bms_file_name, 'wb') as fh:
            pickle.dump(self.orientation, fh)
            pickle.dump(self.extraction_models, fh)
            pickle.dump(self.setup, fh)

    def load(self, bms_file_name):

        h5_file_name = str(bms_file_name)[:-4] + '.h5'

        if not os.path.exists(bms_file_name):
            return

        self.set_file(h5_file_name)

        with open(bms_file_name, 'rb') as fh:
            self.orientation = pickle.load(fh)
            self.extraction_models = pickle.load(fh)
            self.setup = pickle.load(fh)
