import visa
from pyvisa.errors import  VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal
from time import sleep


class SunEC1xChamber(QObject):
    # Place signals here or they won't work

    def __init__(self, parent=None, gpib_addr=None):
        super().__init__()

        self.rm = visa.ResourceManager()
        if gpib_addr is not None:
            self.sun_addr = gpib_addr
        else:
            self.sun_addr = ''

        self.sun = self.connect_sun()

    def connect_sun(self):
        if self.sun_addr != '':
            instruments = self.rm.list_resources()

            for instr in instruments:
                curr_instr = self.rm.open_resource(instr, open_timeout=0.5)
                # if the first 29 characters of the returned string match the LCR ID return
                try:
                    curr_instr.query("*IDN?")
                    try:
                        curr_instr.close()
                    except AttributeError:
                        print('Error closing instrument that should be open')
                except VisaIOError:
                    print('Instrument at {} did not accept ID query, assuming'
                          ' this is the sun environmental chamber'.format(
                            instr))
                    return curr_instr

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
