from Instrument_Interfaces.Agilent_E4980A_Constants import *

import pyvisa
from pyvisa.errors import VisaIOError
from PyQt5.QtCore import QObject, pyqtSignal
from time import sleep


class AgilentE4980A(QObject):
    # This signal needs to be defined before the __init__ in order to allow it to work
    new_data = pyqtSignal(list)
    
    def __init__(self, gpib_addr=None):
        super(AgilentE4980A, self).__init__()

        self.rm = pyvisa.ResourceManager()
        self.lcr_addr = gpib_addr

        if self.lcr_addr is None:
            try:
                self.lcr = self.connect_lcr()
            except NameError:
                print("Could not connect to lcr. GPIB address not found.")
                self.manual_connect_lcr()
        else:
            self.lcr = pyvisa.ResourceManager().open_resource(self.lcr_addr)

    def connect_lcr(self):
        instruments = self.rm.list_resources()

        for instr in instruments:
            curr_instr = self.rm.open_resource(instr, open_timeout=0.5)
            # if the first 29 characters of the returned string match the LCR ID return
            try:
                if curr_instr.query("*IDN?")[0:28] == ID_STR:
                    return curr_instr
                else:
                    try:
                        curr_instr.close()
                    except AttributeError:
                        print('Error closing instrument that should be open')
            except VisaIOError:
                curr_instr.close()

    def clear_status(self, write_or_build='write'):
        command = '*CLS'

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Visa Error on resetting LCR status registers: {}".format(error.abbreviation))
        elif write_or_build.lower() == 'build':
            return command

    def impedance_range(self, imp_range, write_or_build='write'):
        if imp_range == 'auto':
            command = ':FUNC:IMP:RANG:AUTO ON'
        elif imp_range in VALID_IMP_RANGES:
            command = ':FUNC:IMP:RANG {}'.format(imp_range)
        else:
            print('Invalid impedance range supplied.')
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting impedance range: {}\nRetrying...'.format(error.abbreviation))
                self.impedance_range(imp_range)
        elif write_or_build.lower() == 'build':
            return command

    def function(self, function, write_or_build='write'):
        try:
            command = ':FUNC:IMP {}'.format(FUNC_DICT[function])
        except KeyError:
            print('Invalid lcr function supplied: {}'.format(function))
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR function: {}\nRetrying...'.format(error.abbreviation))
                self.function(function)
        elif write_or_build.lower() == 'build':
            return command

    def trigger_source(self, source, write_or_build='write'):
        try:
            command = ':TRIG:SOUR {}'.format(TRIG_SOURCE_DICT[source])
        except KeyError:
            print('Invalid trigger source: {}'.format(source))
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR trigger source: {}\nRetrying...'.format(error.abbreviation))
                self.trigger_source(source)
        elif write_or_build.lower() == 'build':
            return command

    def trigger_init(self, write_or_build='write'):
        command = ':INIT'

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on initializing LCR trigger: {}\nRetrying...'.format(error.abbreviation))
                self.trigger_init()
        elif write_or_build.lower() == 'build':
            return command

    def trigger_delay(self, delay, write_or_build='write'):
        command = ':TRIG:TDEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR trigger delay: {}\nRetrying...'.format(error.abbreviation))
                self.trigger_delay(delay)
        elif write_or_build.lower() == 'build':
            return command

    def step_delay(self, delay, write_or_build='write'):
        command = ':TRIG:DEL {}'.format(delay)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR step delay: {}\nRetrying...'.format(error.abbreviation))
                self.function(delay)
        elif write_or_build.lower() == 'build':
            return command

    def measurement_aperture(self, time: str, avg, write_or_build='write'):
        try:
            command = ':APER {}, {}'.format(MEASURE_TIME_DICT[time], avg)
        except KeyError:
            print('Invalid measurement time supplied: {}'.format(time))
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR measurement aperature: {}\nRetrying...'.format(error.abbreviation))
                self.function(time, avg)
        elif write_or_build.lower() == 'build':
            return command

    def signal_frequency(self, freq, write_or_build='write'):
        command = ':FREQ {}'.format(freq)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR signal frequency: {}\nRetrying...'.format(error.abbreviation))
                self.signal_frequency(freq)
        elif write_or_build.lower() == 'build':
            return command

    def get_signal_frequency(self):
        try:
            freq = self.lcr.query(':FREQ?')
        except VisaIOError as error:
            print('Error on getting LCR signal frequency: {}\nRetrying...'.format(error.abbreviation))
            self.get_signal_frequency()

        return float(freq)

    def signal_level(self, signal_type: str, level, write_or_build='write'):
        if signal_type.lower() == 'voltage':
            command = ':VOLT {}'.format(level)
        elif signal_type.lower() == 'current':
            command = ':CURR {}'.format(level)
        else:
            print('Invalid signal type supplied')
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR signal type/level: {}\nRetrying...'.format(error.abbreviation))
                self.signal_level(signal_type, level)
        elif write_or_build.lower() == 'build':
            return command
    
    def dc_bias_state(self, state, write_or_build='write'):
        if state.lower() == 'on':
            state = 'ON'
        elif state.lower() == 'off':
            state = 'OFF'

        command = ':BIAS:STAT {}'.format(state)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR bias state: {}\nRetrying...'.format(error.abbreviation))
                self.dc_bias_state(state)
        elif write_or_build.lower() == 'build':
            return command

    def dc_bias_level(self, bias_type, level, write_or_build='write'):
        if bias_type.lower() == 'voltage':
            command = ':BIAS:VOLT {}'.format(level)
        elif bias_type.lower() == 'current':
            command = ':BIAS:CURR {}'.format(level)
        else:
            print('Invalid bias type supplied')
            return

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print('Error on setting LCR bias level: {}\nRetrying...'.format(error.abbreviation))
                self.dc_bias_level(bias_type, level)
        elif write_or_build.lower() == 'build':
            return command

    def enable_short_correction(self, enable=True, write_or_build='write'):
        if isinstance(enable, bool):
            enable = 'ON' if enable else 'OFF'
        elif isinstance(enable, str) and enable.upper() in ['ON', 'OFF']:
            enable = enable.upper()
        else:
            raise ValueError("Invalid enable value provided")

        command = ':CORR:SHORT:STAT {}'.format(enable)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on setting the short correction to {}. Error: {}".format(enable, error.abbreviation))
                return self.enable_short_correction()

    def enable_open_correction(self, enable=True, write_or_build='write'):
        if isinstance(enable, bool):
            enable = 'ON' if enable else 'OFF'
        elif isinstance(enable, str) and enable.upper() in ['ON', 'OFF']:
            enable = enable.upper()
        else:
            raise ValueError("Invalid enable value provided")

        command = ':CORR:OPEN:STAT {}'.format(enable)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on setting the open correction to {}. Error: {}".format(enable, error.abbreviation))
                return self.enable_short_correction()

    def enable_load_correction(self, enable=True, write_or_build='write'):
        if isinstance(enable, bool):
            enable = 'ON' if enable else 'OFF'
        elif isinstance(enable, str) and enable.upper() in ['ON', 'OFF']:
            enable = enable.upper()
        else:
            raise ValueError("Invalid enable value provided")

        command = ':CORR:LOAD:STAT {}'.format(enable)

        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on setting the load correction to {}. Error: {}".format(enable, error.abbreviation))
                return self.enable_short_correction()

    def measure_short_correction(self, write_or_build='write'):
        command = ':CORR:SHORT:EXEC'
        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on sending command to execute short correction. Error: {}".format(error.abbreviation))

    def measure_open_correction(self, write_or_build='write'):
        command = ':CORR:OPEN:EXEC'
        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on sending command to execute open correction. Error: {}".format(error.abbreviation))

    def measure_load_correction(self, write_or_build='write'):
        command = ':CORR:LOAD:EXEC'
        if write_or_build.lower() == 'write':
            try:
                self.lcr.write(command)
            except VisaIOError as error:
                print("Error on sending command to execute LOAD correction. Error: {}".format(error.abbreviation))

    def get_data(self):
        try:
            rec_data = self.lcr.query(':FETC?')
            rec_data = rec_data.rstrip().split(',')
            rec_data = [float(x) for x in rec_data]
        except VisaIOError as error:
            print('Error on retrieving data from LCR: {}\nRetrying...'.format(error.abbreviation))
            sleep(0.1)
            self.clear_status()
            return self.get_data()
        except ValueError as error:
            print("Unable to read data from LCR - Float conversion error ({}) Retrying...".format(error))
            sleep(0.1)
            self.clear_status()
            return self.get_data()
        else:
            freq = self.get_signal_frequency()
            rec_data.insert(0, freq)
            self.new_data.emit(rec_data)
            return rec_data