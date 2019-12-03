# ToDo: Add sun chamber monitoring and control to the norm Cap_Freq Measurements, allowing for temperature dependent
#  studies of materials without manual intervention
import sys

import visa
from PyQt5.QtCore import QThread

from Sun_EC1X import SunEC1xChamber
# from fake_sun import SunEC1xChamber
from Cap_Freq import CapFreqWidget, CapFreqMeasureWorkerObject
from Agilent_E4980A import AgilentE4980A
# from fake_E4980 import AgilentE4980A
from File_Print_Headers import *
from statistics import stdev, mean
import pandas as pd
from time import sleep
from PyQt5.QtWidgets import QLineEdit, QLabel, QGroupBox, QRadioButton, QApplication


class CapFreqTempWidget(CapFreqWidget):

    def __init__(self, lcr: AgilentE4980A, sun: SunEC1xChamber, measuring_thread=QThread()):

        self.sun = sun
        super().__init__(lcr=lcr, measuring_thread=measuring_thread, ui_path='./src/ui/cap_freq_temp_tabs.ui')
        print('Initializing Capacitance-Frequency-Temperature Widget')
        self.dwell = 10
        self.ramp = 5
        self.stab_int = 5
        # Override from base class to add a temperature field
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Measurement Delay [s]',
                                    'Temperature Set Point [°C]']

        self.gbox_thermal_settings = self.findChild(QGroupBox, 'gbox_thermal_settings')
        self.ln_ramp = self.findChild(QLineEdit, 'ln_ramp')
        self.ln_dwell = self.findChild(QLineEdit, 'ln_dwell')
        self.ln_stab_int = self.findChild(QLineEdit, 'ln_stab_int')
        self.ln_temp_tol = self.findChild(QLineEdit, 'ln_temp_tol')
        self.ln_stdev_tol = self.findChild(QLineEdit, 'ln_stdev_tol')

        self.radio_chamber_tc = self.findChild(QRadioButton, 'radio_chamber_tc')
        self.radio_user_tc = self.findChild(QRadioButton, 'radio_user_tc')
        self.gbox_curr_temp = self.findChild(QGroupBox, 'gbox_curr_temp')
        self.lbl_curr_temp = self.findChild(QLabel, 'lbl_curr_temp')
        self.lbl_curr_meas_temp = self.findChild(QLabel, 'lbl_curr_meas_temp')

        self.init_setup_table()
        self.init_connections()

    def init_measure_worker(self):
        # Initialize worker object and move instruments to the worker thread.
        self.measuring_worker = CapFreqTempMeasureWorkerObject(self)
        print('moving worker')
        self.measuring_worker.moveToThread(self.measuring_thread)
        # if self.move_lcr:
        #     print('moving lcr')
        #     self.lcr.moveToThread(self.measuring_thread)
        # print('moving sun')
        # self.sun.moveToThread(self.measuring_thread)

    def init_setup_table(self):
        super().init_setup_table()
        self.table_meas_setup.setColumnCount(6)
        self.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.add_table_items()
        self.table_meas_setup.item(0, 5).setText('25')

    def init_connections(self):
        super().init_connections()
        self.ln_dwell.editingFinished.connect(self.change_dwell)
        self.ln_ramp.editingFinished.connect(self.change_ramp)
        self.ln_stab_int.editingFinished.connect(self.change_stab_int)

    def change_dwell(self):
        self.dwell = float(self.ln_dwell.text())

    def change_ramp(self):
        self.ramp = float(self.ln_ramp.text())

    def change_stab_int(self):
        self.stab_int = float(self.ln_stab_int.text())

    def move_instr_to_worker_thread(self):
        self.lcr.moveToThread(self.measuring_thread)
        self.sun.moveToThread(self.measuring_thread)

    def update_live_readout(self, data: list):
        super().update_live_readout(data)
        # Going to try directly getting the temperature in this function,
        #  should keep compatibility simple.
        if self.radio_chamber_tc.isChecked():
            self.lbl_curr_temp.setText(str(self.sun.get_temp()))
        elif self.radio_user_tc.isChecked():
            self.lbl_curr_temp.setText(str(self.sun.get_user_temp()))

    def get_header_vars(self, index, row):
        header_vars = super().get_header_vars(index, row)

        header_vars['ramp'] = self.ramp
        header_vars['dwell'] = self.dwell
        header_vars['stab_int'] = self.stab_int

        return header_vars

    def generate_header(self, index, row):
        header_vars = self.get_header_vars(index, row)

        header = CAP_FREQ_TEMP_HEADER.format(meas_type=self.lcr_function,
                                             meas_date=header_vars['date_now'],
                                             meas_time=header_vars['time_now'],
                                             meas_num=header_vars['meas_number'],
                                             start_freq=header_vars['start'],
                                             stop_freq=header_vars['stop'],
                                             osc_type=header_vars['osc_type'],
                                             osc=header_vars['osc'],
                                             bias_type=header_vars['bias_type'],
                                             bias=header_vars['bias'],
                                             step_delay=self.meas_delay,
                                             ramp=header_vars['ramp'],
                                             dwell=header_vars['dwell'],
                                             stab_int=header_vars['stab_int'],
                                             # ToDo: Verify that these values can be pulled this way. It is
                                             #  going to be way easier if they are. Should be set correctly by
                                             #  the time this function is called.
                                             user_avg=self.measuring_worker.user_avg,
                                             user_stdev=self.measuring_worker.user_stdev,
                                             chamber_avg=self.measuring_worker.chamber_avg,
                                             chamber_stdev=self.measuring_worker.chamber_stdev,
                                             notes='Notes:\t{}'.format(header_vars['notes']))

        return header

    def enable_controls(self, enable: bool):
        super().enable_controls(enable)
        self.gbox_thermal_settings.setEnabled(enable)


class CapFreqTempMeasureWorkerObject (CapFreqMeasureWorkerObject):

    def __init__(self, parent: CapFreqTempWidget):
        super().__init__(parent)
        self.parent = parent
        self.step_temp = 0
        self.user_avg = 0
        self.chamber_avg = 0
        self.user_stdev = 0
        self.chamber_stdev = 0

    # Don't need to override as we aren't adding data to each line, just the
    #  header.
    # def get_out_columns(self):
    #     columns = super().get_out_columns()
    #     columns.append('Chamber Temp [°C]')
    #     columns.append('Chamber Std Dev [°C]')
    #     columns.append('User Temp [°C]')
    #     columns.append('User Std Dev [°C]')
    #
    #     return columns

    def set_test_params(self, row):
        super().set_test_params(row)
        self.step_temp = float(row[self.parent.meas_setup_hheaders[5]])

    def set_current_meas_labels(self):
        super().set_current_meas_labels()
        self.parent.lbl_curr_meas_temp.setText(str(self.step_temp))

    def return_instr_to_main_thread(self):
        self.lcr.moveToThread(QApplication.instance().thread())
        self.sun.moveToThread(QApplication.instance().thread())

    def blocking_func(self):
        user_T = []
        chamber_T = []

        # Send the command to change the temperature
        self.parent.sun.set_setpoint(self.step_temp)

        # Get the current temperature and loop umtil setpoint is achieved
        check_temp = float(self.parent.sun.get_temp())
        if self.step_temp > check_temp:
            while check_temp < self.step_temp:
                check_temp = float(self.parent.sun.get_temp())
                sleep(1)
        elif self.step_temp < check_temp:
            while check_temp > self.step_temp:
                check_temp = float(self.parent.sun.get_temp())
                sleep(1)

        # After reaching setpoint, check stability
        # ToDo: Make the print statements here appear in a pop-up with a progress bar
        print('Beginning temperature stability check...')
        count = 0
        for i in range(0, self.parent.dwell * 60):
            if count % self.parent.stab_int == 0:
                user_T.append(self.parent.sun.get_user_temp())
                chamber_T.append(self.parent.sun.get_temp())
                print('.', end=' ')
            else:
                print('.', end='')
            count += 1
            sleep(1)
        print('Temperature equilibration complete.')

        self.user_avg = mean(user_T)
        self.user_stdev = stdev(user_T, self.user_avg)
        self.chamber_avg = mean(chamber_T)
        self.chamber_stdev = stdev(chamber_T, self.chamber_avg)

        temp_tol = float(self.parent.ln_temp_tol.text())
        stdev_tol = float(self.parent.ln_stdev_tol.text())

        if self.user_avg > temp_tol or self.chamber_avg > temp_tol or self.user_stdev > stdev_tol or self.chamber_stdev > stdev_tol:
            self.blocking_func()

        # Add the standard measurement delay from cap freq
        super().blocking_func()

    # Not adding data to each value line for now. Just to the measurement header.
    # def read_new_data(self):
    #     # Read the LCR and append temperature data
    #     data = self.parent.lcr.get_data()
    #     # ToDo: Should temperature be recorded with each step?
    #     data.append(self.chamber_avg)
    #     data.append(self.chamber_stdev)
    #     data.append(self.user_avg)
    #     data.append(self.user_stdev)
    #
    #     data = pd.Series(data, index=self.data_df.columns)

    # ToDo: Override all functions called in the measure method to give temperature measurements as well.


try:
    standalone = sys.argv[1]
except IndexError:
    standalone = False

if standalone == 'capfreqtemp':
    lcr = AgilentE4980A(parent=None, gpib_addr='GPIB0::18::INSTR')
    sun = SunEC1xChamber(parent=None, gpib_addr='GPIB0::6::INSTR')
    app = QApplication(sys.argv)
    main_window = CapFreqTempWidget(lcr=lcr, sun=sun)
    main_window.show()
    sys.exit(app.exec_())
