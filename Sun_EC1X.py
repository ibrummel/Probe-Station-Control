import visa
from pyvisa.errors import  VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal

class SunEC1xChamber(QObject):
    # Place signals here or they won't work

    def __init__(self):
        super().__init__()
