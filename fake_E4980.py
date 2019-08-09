from Agilent_E4980A_Constants import *

import visa
from PyQt5.QtWidgets import QWidget, QDialog, QComboBox, QPushButton, QFormLayout, QLabel
from InstrumentSelectBox import InstrumentSelectBox


class AgilentE4980A(QWidget):
    def __init__(self):
        super().__init__()

        self.rm = visa.ResourceManager()
        self.select_box = InstrumentSelectBox(self.rm)
        self.lcr_addr = ''

        try:
            self.connect_lcr()
        except NameError:
            print("Could not connect to lcr. GPIB address not found.")
            self.manual_connect_lcr()

    def connect_lcr(self):
        print('"Connected to instrument"')

    def manual_connect_lcr(self):
        self.select_box.exec_()

    def impedance_range(self, imp_range, write_or_build='write'):
        if imp_range == 'auto':
            command = ':FUNC:IMP:RANG:AUTO ON'
        elif imp_range in VALID_IMP_RANGES:
            command = ':FUNC:IMP:RANG {}'.format(imp_range)

        print(command)

    def function(self, function, write_or_build='write'):
        try:
            command = ':FUNC:IMP {}'.format(FUNC_DICT[function])
        except KeyError:
            print('Invalid lcr function supplied: {}'.format(function))

        print(command)

    def trigger_source(self, source, write_or_build='write'):
        try:
            command = ':TRIG:SOUR {}'.format(TRIG_SOURCE_DICT[source])
        except KeyError:
            print('Invalid trigger source: {}'.format(source))

        print(command)

    def trigger_init(self, write_or_build='write'):
        command = ':INIT'

        print(command)

    def trigger_delay(self, delay: float, write_or_build='write'):
        command = ':TRIG:TDEL {}'.format(delay)

        print(command)

    def step_delay(self, delay: float, write_or_build='write'):
        command = ':TRIG:DEL {}'.format(delay)

        print(command)

    def measurement_aperture(self, time: str, avg: int, write_or_build='write'):
        try:
            command = ':APER {}, {}'.format(MEASURE_TIME_DICT[time], avg)
        except KeyError:
            print('Invalid measurement time supplied: {}'.format(time))

        print(command)

    def signal_frequency(self, freq: int, write_or_build='write'):
        command = ':FREQ {}'.format(int(freq))

        print(command)

    def signal_voltage(self, voltage: float, write_or_build='write'):
        command = ':VOLT {}'.format(voltage)

        print(command)

    def signal_current(self, current: float, write_or_build='write'):
        command = ':CURR {}'.format(current)

        print(command)

    def dc_bias_state(self, state: str, write_or_build='write'):
        if state.lower() == 'on':
            state = 'ON'
        elif state.lower() == 'off':
            state = 'OFF'

        command = ':BIAS:STAT {}'.format(state)

        print(command)

    def dc_bias_voltage(self, voltage: float, write_or_build='write'):
        command = ':BIAS:VOLT {}'.format(voltage)

        print(command)

    def dc_bias_current(self, current: float, write_or_build='write'):
        command = ':BIAS:VOLT {}'.format(current)

        print(command)

    def get_data(self):

        return ['Data', 'Fetched', '1']

    def get_function_parameters(self):
        func_params = PARAMETERS_BY_FUNC[self.lcr.query(':FUNC:IMP?').rstrip()]

        return func_params
