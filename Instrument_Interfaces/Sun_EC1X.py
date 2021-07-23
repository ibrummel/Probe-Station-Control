import pyvisa
from pyvisa.errors import VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal
from time import sleep


class SunEC1xChamber(QObject):
    # Place signals here or they won't work

    def __init__(self, gpib_addr=None):
        super(SunEC1xChamber, self).__init__()

        self.rm = pyvisa.ResourceManager()
        if gpib_addr is not None:
            self.sun_addr = gpib_addr
        else:
            self.sun_addr = ''

        self.sun = self.connect_sun()

    def connect_sun(self):
        if self.sun_addr == '':
            instruments = self.rm.list_resources()
        else:
            instruments = [self.sun_addr]

        for instr in instruments:
            curr_instr = self.rm.open_resource(instr, open_timeout=0.5)
            try:
                version_str = curr_instr.query("VER?")

                if version_str == "SUN EC1x V_10.10\r\n":
                    print("Successfully connected to sun with version string {} "
                          "at GPIB address {}".format(version_str, instr))
                    return curr_instr
                else:
                    try:
                        curr_instr.close()
                    except AttributeError:
                        print('Error closing instrument that should be open')
            except VisaIOError:
                pass

        raise ValueError("Failed to find sun chamber. Please reinitialize object with valid address.")

    def get_temp(self):
        try:
            return float(self.sun.query('temp?'))
        except VisaIOError as error:
            print('Error on getting chamber temp: {}'.format(error.abbreviation))
            return -9999.0

    def get_user_temp(self):
        try:
            return float(self.sun.query('uchan?'))
        except VisaIOError as error:
            print('Error on getting user temp: {}'.format(error.abbreviation))
            return -9999.0

    def set_setpoint(self, stpt: float):
        try:
            self.sun.write('set={}'.format(stpt))
        except VisaIOError as error:
            print('Error on writing setpoint: {}'.format(error.abbreviation))

    def get_setpoint(self):
        try:
            return float(self.sun.query('set?'))
        except VisaIOError as error:
            print('Error on getting setpoint: {}').format(error.abbreviation)
            return -9999.0

    def set_ramprate(self, ramprate: float):
        try:
            self.sun.write('RATE={}'.format(ramprate))
        except VisaIOError as error:
            print('Error on writing ramprate: {}'.format(error.abbreviation))

    def get_ramprate(self):
        try:
            return float(self.sun.query("rate?"))
        except VisaIOError as error:
            print("Error on getting ramp rate: {}".format(error.abbreviation))
            return -9999.0

