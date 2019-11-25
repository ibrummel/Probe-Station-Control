import visa
from pyvisa.errors import  VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal


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
                print(instr)
                curr_instr = self.rm.open_resource(instr, open_timeout=0.5)
                # if the first 29 characters of the returned string match the LCR ID return
                try:
                    curr_instr.query("*IDN?")[0:28]
                    try:
                        curr_instr.close()
                    except AttributeError:
                        print('Error closing instrument that should be open')
                except VisaIOError:
                    print('Attempt to get identification string failed. '
                          'Instrument at {} did not accept ID query'.format(
                            instr))
                    return curr_instr

    def get_temp(self):
        return float(self.sun.query('temp?'))

    def get_user_temp(self):
        return float(self.sun.query('uchan?'))

    def set_setpoint(self, stpt: float):
        self.sun.write('set={}'.format(stpt))