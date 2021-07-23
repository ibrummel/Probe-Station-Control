import visa
from pyvisa.errors import  VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal


class SunEC1xChamber(QObject):
    # Place signals here or they won't work

    def __init__(self, parent=None, gpib_addr=None):
        super().__init__()

        self.sun = self.connect_sun()
        self.temp = 25

    def connect_sun(self):
        return True

    def get_temp(self):
        return self.temp
    def get_user_temp(self):
        return self.temp

    def set_setpoint(self, stpt: float):
        self.temp = stpt