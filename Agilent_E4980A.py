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
            self.lcr = self.connect_lcr()
        except NameError:
            print("Could not connect to lcr. GPIB address not found.")
            self.manual_connect_lcr()

    def connect_lcr(self):
        instruments = self.rm.list_resources()

        for instr in self.instruments:
            curr_instr = self.rm.open_resource(instr)
            # if the first 29 characters of the returned string match the LCR ID return
            if curr_instr.query("IDN?")[0:28] == ID_STR:
                return curr_instr
            else:
                self.lcr.close()

    def manual_connect_lcr(self):
        self.select_box.exec_()

    def impedance_range(self, imp_range, write_or_build='write'):
        if imp_range == 'auto':
            command = ':FUNC:IMP:RANG:AUTO ON'
        elif imp_range in VALID_IMP_RANGES:
            command = ':FUNC:IMP:RANG {}'.format(imp_range)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def function(self, function, write_or_build='write'):
        try:
            command = ':FUNC:IMP {}'.format(FUNC_DICT[function])
        except KeyError:
            print('Invalid lcr function supplied: {}'.format(function))

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def trigger_source(self, source, write_or_build='write'):
        try:
            command = ':TRIG:SOUR {}'.format(TRIG_SOURCE_DICT[source])
        except KeyError:
            print('Invalid trigger source: {}'.format(source))

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def trigger_init(self, write_or_build='write'):
        command = ':INIT'

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def trigger_delay(self, delay: float, write_or_build='write'):
        command = ':TRIG:TDEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def step_delay(self, delay: float, write_or_build='write'):
        command = ':TRIG:DEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def measurement_aperture(self, time: str, avg: int, write_or_build='write'):
        try:
            command = ':APER {}, {}'.format(MEASURE_TIME_DICT[time], avg)
        except KeyError:
            print('Invalid measurement time supplied: {}'.format(time))

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def signal_frequency(self, freq: int, write_or_build='write'):
        command = ':FREQ {}'.format(int(freq))

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def signal_voltage(self, voltage: float, write_or_build='write'):
        command = ':VOLT {}'.format(voltage)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def signal_current(self, current: float, write_or_build='write'):
        command = ':CURR {}'.format(current)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command
    
    def dc_bias_state(self, state: str, write_or_build='write'):
        if state.lower() == 'on':
            state = 'ON'
        elif state.lower() == 'off':
            state = 'OFF'

        command = ':BIAS:STAT {}'.format(state)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def dc_bias_voltage(self, voltage: float, write_or_build='write'):
        command = ':BIAS:VOLT {}'.format(voltage)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def dc_bias_current(self, current: float, write_or_build='write'):
        command = ':BIAS:VOLT {}'.format(current)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def get_data(self):
        data = self.lcr.query(':FETC?')

        return data.rstrip().split(',')

    def get_function_parameters(self):
        func_params = PARAMETERS_BY_FUNC[self.lcr.query(':FUNC:IMP?').rstrip()]

        return func_params
