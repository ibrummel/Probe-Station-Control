from Agilent_E4980A_Constants import *

import visa
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal
from InstrumentSelectBox import InstrumentSelectBox


class AgilentE4980A(QObject):
    # This signal needs to be defined before the __init__ in order to allow it to work
    new_data = pyqtSignal(list)
    
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

        for instr in instruments:
            curr_instr = self.rm.open_resource(instr)
            # if the first 29 characters of the returned string match the LCR ID return
            if curr_instr.query("*IDN?")[0:28] == ID_STR:
                return curr_instr
            else:
                try:
                    curr_instr.close()
                except AttributeError:
                    print('Error closing instrument that should be open')

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

    def trigger_delay(self, delay, write_or_build='write'):
        command = ':TRIG:TDEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def step_delay(self, delay, write_or_build='write'):
        command = ':TRIG:DEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def measurement_aperture(self, time: str, avg, write_or_build='write'):
        try:
            command = ':APER {}, {}'.format(MEASURE_TIME_DICT[time], avg)
        except KeyError:
            print('Invalid measurement time supplied: {}'.format(time))

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def signal_frequency(self, freq, write_or_build='write'):
        command = ':FREQ {}'.format(freq)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def get_signal_frequency(self):
        freq = self.lcr.query(':FREQ?')
        return float(freq)

    def signal_level(self, signal_type: str, level, write_or_build='write'):
        if signal_type.lower() == 'voltage':
            command = ':VOLT {}'.format(level)
        elif signal_type.lower() == 'current':
            command = ':CURR {}'.format(level)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command
    
    def dc_bias_state(self, state, write_or_build='write'):
        if state.lower() == 'on':
            state = 'ON'
        elif state.lower() == 'off':
            state = 'OFF'

        command = ':BIAS:STAT {}'.format(state)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def dc_bias_level(self, bias_type, level, write_or_build='write'):
        if bias_type.lower() == 'voltage':
            command = ':BIAS:VOLT {}'.format(level)
        elif bias_type.lower() == 'current':
            command = ':BIAS:CURR {}'.format(level)

        if write_or_build.lower() == 'write':
            self.lcr.write(command)
        elif write_or_build.lower() == 'build':
            return command

    def get_data(self):
        data = self.lcr.query(':FETC?')
        data = data.rstrip().split(',')

        self.new_data.emit(data)
        return data


    def get_function_parameters(self):
        func_params = PARAMETERS_BY_FUNC[self.lcr.query(':FUNC:IMP?').rstrip()]

        return func_params
