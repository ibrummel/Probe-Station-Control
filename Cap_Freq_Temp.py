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
from statistics import stdev, mean, StatisticsError
import pandas as pd
from time import sleep
import datetime
from pyvisa.errors import VisaIOError
from PyQt5.QtWidgets import QLineEdit, QLabel, QGroupBox, QRadioButton, QApplication, QCheckBox


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
        self.ln_ramp.setText('5.0')
        self.ln_dwell = self.findChild(QLineEdit, 'ln_dwell')
        self.ln_dwell.setText('10')
        self.ln_stab_int = self.findChild(QLineEdit, 'ln_stab_int')
        self.ln_stab_int.setText('5')
        self.ln_temp_tol = self.findChild(QLineEdit, 'ln_temp_tol')
        self.ln_temp_tol.setText('0.5')
        self.ln_stdev_tol = self.findChild(QLineEdit, 'ln_stdev_tol')
        self.ln_stdev_tol.setText('0.2')
        self.check_z_stability = self.findChild(QCheckBox, 'check_z_stability')
        self.ln_z_stdev_tol = self.findChild(QLineEdit, 'ln_z_stdev_tol')
        self.ln_z_stdev_tol.setText('500')
        self.check_return_to_rt = self.findChild(QCheckBox, 'check_return_to_rt')

        self.radio_chamber_tc = self.findChild(QRadioButton, 'radio_chamber_tc')
        self.radio_user_tc = self.findChild(QRadioButton, 'radio_user_tc')
        self.gbox_curr_temp = self.findChild(QGroupBox, 'gbox_curr_temp')
        self.lbl_curr_temp = self.findChild(QLabel, 'lbl_curr_temp')
        self.lbl_curr_meas_temp = self.findChild(QLabel, 'lbl_curr_meas_temp')

        self.init_setup_table()

    def init_measure_worker(self):
        # Initialize worker object and move instruments to the worker thread.
        self.measuring_worker = CapFreqTempMeasureWorkerObject(self)
        print('moving worker')
        self.measuring_worker.moveToThread(self.measuring_thread)
        print('moving lcr')
        self.lcr.moveToThread(self.measuring_thread)
        print('moving sun')
        self.sun.moveToThread(self.measuring_thread)

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
        if self.enable_live_vals:
            try:
                if self.radio_chamber_tc.isChecked():
                    self.lbl_curr_temp.setText(str(self.sun.get_temp()))
                elif self.radio_user_tc.isChecked():
                    self.lbl_curr_temp.setText(str(self.sun.get_user_temp()))
            except VisaIOError:
                print('Error on getting temperature from sun chamber')

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
                                             user_avg=self.measuring_worker.user_avg,
                                             user_stdev=self.measuring_worker.user_stdev,
                                             chamber_avg=self.measuring_worker.chamber_avg,
                                             chamber_stdev=self.measuring_worker.chamber_stdev,
                                             z_stdev=self.measuring_worker.z_stdev,
                                             notes='Notes:\t{}'.format(header_vars['notes']))

        return header

    def enable_controls(self, enable: bool):
        super().enable_controls(enable)
        self.gbox_thermal_settings.setEnabled(enable)


class CapFreqTempMeasureWorkerObject(CapFreqMeasureWorkerObject):

    def __init__(self, parent: CapFreqTempWidget):
        super().__init__(parent)
        self.parent = parent
        self.step_temp = 0
        self.user_avg = 0
        self.chamber_avg = 0
        self.user_stdev = 0
        self.chamber_stdev = 0
        self.z_stdev = 0

    def set_test_params(self, row):
        super().set_test_params(row)
        self.step_temp = float(row[self.parent.meas_setup_hheaders[5]])

    def set_current_meas_labels(self):
        super().set_current_meas_labels()
        self.parent.lbl_curr_meas_temp.setText(str(self.step_temp))

    def return_instr_to_main_thread(self):
        self.lcr.moveToThread(QApplication.instance().thread())
        # self.sun.moveToThread(QApplication.instance().thread())

    def measurement_cleanup(self):
        if self.parent.check_return_to_rt.isChecked():
            self.parent.sun.set_setpoint(25.0)
            print('Sun setpoint moved to 25C.')

    def blocking_func(self):
        user_T = []
        chamber_T = []
        z = []

        # Send the command to change the temperature
        self.parent.sun.set_setpoint(self.step_temp)

        # Get the current temperature and loop umtil setpoint is achieved
        check_temp = float(self.parent.sun.get_temp())
        if self.step_temp > check_temp:
            while check_temp < self.step_temp:
                check_temp = float(self.parent.sun.get_temp())
                self.parent.lbl_curr_temp.setText(str(check_temp))
                sleep(1)
                if self.stop:
                    break
        elif self.step_temp < check_temp:
            while check_temp > self.step_temp:
                check_temp = float(self.parent.sun.get_temp())
                self.parent.lbl_curr_temp.setText(str(check_temp))
                sleep(1)
                if self.stop:
                    break

        # After reaching setpoint, check stability
        # ToDo: Make the print statements here appear in a pop-up with a progress bar
        print('Beginning temperature stability check at {temp}...'.format(temp=self.step_temp))
        self.parent.enable_live_plots = False
        count = 0
        for i in range(0, int(self.parent.dwell * 60)):
            if count % self.parent.stab_int == 0:
                user_T.append(self.parent.sun.get_user_temp())
                sleep(0.1)
                chamber_T.append(self.parent.sun.get_temp())
                z.append(self.parent.lcr.get_data()[1])
                if self.parent.radio_chamber_tc.isChecked():
                    self.parent.lbl_curr_temp.setText(str(chamber_T[-1]))
                elif self.parent.radio_user_tc.isChecked():
                    self.parent.lbl_curr_temp.setText(str(user_T[-1]))
            count += 1
            sleep(1)
            print("Stability Check in Progress {} remaining"
                  .format(str(datetime.timedelta(seconds=int(self.parent.dwell * 60)-i)), end="\r"))
            if self.stop:
                break
        if self.stop:
            return
        print("Temperature equilibration complete. {} remaining".format(str(datetime.timedelta(seconds=0)), end="\r"))
        self.parent.enable_live_plots = True

        try:
            self.user_avg = mean(user_T)
            self.user_stdev = stdev(user_T, self.user_avg)
            self.chamber_avg = mean(chamber_T)
            self.chamber_stdev = stdev(chamber_T, self.chamber_avg)
            self.z_stdev = stdev(z, mean(z))
        except StatisticsError:
            print('Error on performing statistics calculations.')
            self.user_avg = 99999
            self.user_stdev = 99999
            self.chamber_avg = 99999
            self.chamber_stdev = 99999
            self.z_stdev = 99999

        temp_tol = float(self.parent.ln_temp_tol.text())
        stdev_tol = float(self.parent.ln_stdev_tol.text())
        z_stdev_tol = float(self.parent.ln_z_stdev_tol.text())

        if abs(self.chamber_avg - self.step_temp) > temp_tol or self.chamber_stdev > stdev_tol:
            print('Temperature ({delta} vs {deltol}) or standard deviation ({stdev} vs {stdevtol}) '
                  'outside of tolerance.'.format(delta=abs(self.chamber_avg - self.step_temp), deltol=temp_tol,
                                                 stdev=self.chamber_stdev, stdevtol=stdev_tol))
            self.blocking_func()
        print('Temperature readings within tolerance')
        if self.parent.check_z_stability.isChecked():
            if self.z_stdev > z_stdev_tol:
                print('Impedance variation outside of tolerance: Tolerance={tol}, Measured Stdev={stdev}'
                      .format(tol=z_stdev_tol, stdev=self.z_stdev))
                self.blocking_func()
            print('Impedance stability within tolerance.')

        # Add the standard measurement delay from cap freq
        super().blocking_func()


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
