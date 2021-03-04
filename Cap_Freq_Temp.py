import sys
from PyQt5.QtCore import QThread
from Sun_EC1X import SunEC1xChamber
# from fake_sun import SunEC1xChamber
from Cap_Freq import CapFreqWidget, CapFreqMeasureWorkerObject
# from Agilent_E4980A import AgilentE4980A
from fake_E4980 import AgilentE4980A
from File_Print_Headers import *
from statistics import stdev, mean, StatisticsError
from Static_Functions import to_sigfigs
from time import sleep, time
from datetime import timedelta
from pyvisa.errors import VisaIOError
from PyQt5.QtWidgets import QLineEdit, QLabel, QGroupBox, QRadioButton, QApplication, QCheckBox


class CapFreqTempWidget(CapFreqWidget):

    def __init__(self, lcr: AgilentE4980A, sun: SunEC1xChamber, measuring_thread=QThread()):

        self.sun = sun
        super().__init__(lcr=lcr, measuring_thread=measuring_thread, ui_path='./src/ui/cap_freq_temp_tabs.ui')
        # print('Initializing Capacitance-Frequency-Temperature Widget')
        self.dwell = 10
        self.ramp = 5
        self.stab_int = 5
        # Override from base class to add a temperature field
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Equilibration Delay [s]',
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
        self.check_always_stab = self.findChild(QCheckBox, 'check_always_stab')

        self.radio_chamber_tc = self.findChild(QRadioButton, 'radio_chamber_tc')
        self.radio_user_tc = self.findChild(QRadioButton, 'radio_user_tc')
        self.gbox_curr_temp = self.findChild(QGroupBox, 'gbox_curr_temp')
        self.lbl_curr_temp = self.findChild(QLabel, 'lbl_curr_temp')
        self.lbl_curr_meas_temp = self.findChild(QLabel, 'lbl_curr_meas_temp')

        self.init_setup_table()
        self.change_dwell()
        self.change_ramp()
        self.change_stab_int()

    def init_measure_worker(self):
        # Initialize worker object and move instruments to the worker thread.
        self.measuring_worker = CapFreqTempMeasureWorkerObject(self)
        # print('moving worker')
        self.measuring_worker.moveToThread(self.measuring_thread)
        # print('moving lcr')
        self.lcr.moveToThread(self.measuring_thread)
        # print('moving sun')
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

    def generate_header(self, index, row, external_measurement=False):
        header_vars = self.get_header_vars(index, row)

        if self.measuring_worker.step_temp == self.measuring_worker.prev_step_temp and not self.check_always_stab.isChecked():
            user_avg = str(to_sigfigs(self.measuring_worker.user_avg, 5)) + '*'
            user_stdev = str(to_sigfigs(self.measuring_worker.user_stdev, 5)) + '*'
            chamber_avg = str(to_sigfigs(self.measuring_worker.chamber_avg, 5)) + '*'
            chamber_stdev = str(to_sigfigs(self.measuring_worker.chamber_stdev, 5)) + '*'
            z_stdev = str(to_sigfigs(self.measuring_worker.z_stdev, 5)) + '*'
        else:
            user_avg = str(to_sigfigs(self.measuring_worker.user_avg, 5))
            user_stdev = str(to_sigfigs(self.measuring_worker.user_stdev, 5))
            chamber_avg = str(to_sigfigs(self.measuring_worker.chamber_avg, 5))
            chamber_stdev = str(to_sigfigs(self.measuring_worker.chamber_stdev, 5))
            z_stdev = str(to_sigfigs(self.measuring_worker.z_stdev, 5))

        header = CAP_FREQ_TEMP_HEADER.format(meas_type=self.lcr_function,
                                             meas_date=header_vars['date_now'],
                                             meas_time=header_vars['time_now'],
                                             meas_num=header_vars['meas_number'],
                                             start_freq="External Measurement",
                                             stop_freq="External Measurement",
                                             osc_type="External Measurement",
                                             osc="External Measurement",
                                             bias_type="External Measurement",
                                             bias="External Measurement",
                                             step_delay=self.meas_delay,
                                             ramp=header_vars['ramp'],
                                             dwell=header_vars['dwell'],
                                             stab_int=header_vars['stab_int'],
                                             user_avg=user_avg,
                                             user_stdev=user_stdev,
                                             chamber_avg=chamber_avg,
                                             chamber_stdev=chamber_stdev,
                                             z_stdev=z_stdev,
                                             notes='Notes:\t{}'.format(header_vars['notes']))

        return header

    def enable_controls(self, enable: bool):
        super().enable_controls(enable)
        self.gbox_thermal_settings.setEnabled(enable)


class CapFreqTempMeasureWorkerObject(CapFreqMeasureWorkerObject):

    def __init__(self, parent: CapFreqTempWidget):
        super().__init__(parent)
        self.parent = parent
        self.step_temp = None
        self.user_avg = 0
        self.chamber_avg = 0
        self.user_stdev = 0
        self.chamber_stdev = 0
        self.z_stdev = 0
        self.prev_step_temp = None

    def set_test_params(self, row):
        super().set_test_params(row)
        self.prev_step_temp = self.step_temp
        self.step_temp = float(row[self.parent.meas_setup_hheaders[5]])
        # print("Setting test temperature to {}".format(self.step_temp))

    def set_current_meas_labels(self):
        super().set_current_meas_labels()
        self.parent.lbl_curr_meas_temp.setText(str(self.step_temp))

    def return_instr_to_main_thread(self):
        self.lcr.moveToThread(QApplication.instance().thread())
        # self.sun.moveToThread(QApplication.instance().thread())

    def measurement_cleanup(self):
        if self.parent.check_return_to_rt.isChecked():
            self.parent.sun.set_setpoint(25.0)
            self.meas_status_update.emit('Measurement Finished. Temperature set point: 25°C')
        else:
            self.meas_status_update.emit('Measurement Finished.')
        # Prevent issues with rollover from previous measurements.
        self.step_temp = None
        self.prev_step_temp = None

    def blocking_func(self):
        user_T = []
        chamber_T = []
        z = []

        if self.step_temp != self.prev_step_temp:
            # Send the command to change the temperature
            self.parent.sun.set_setpoint(self.step_temp)
            self.meas_status_update.emit("Waiting for chamber to reach {}...".format(self.step_temp))

            # Get the current temperature and loop umtil setpoint is achieved
            check_temp = float(self.parent.sun.get_temp())
            if self.step_temp > check_temp:
                while check_temp < self.step_temp - float(self.parent.ln_temp_tol.text()):
                    check_temp = float(self.parent.sun.get_temp())
                    self.parent.lbl_curr_temp.setText(str(check_temp))
                    sleep(1)
                    if self.stop:
                        break
            elif self.step_temp < check_temp:
                while check_temp > self.step_temp + float(self.parent.ln_temp_tol.text()):
                    check_temp = float(self.parent.sun.get_temp())
                    self.parent.lbl_curr_temp.setText(str(check_temp))
                    sleep(1)
                    if self.stop:
                        break

        if self.step_temp != self.prev_step_temp or self.parent.check_always_stab.isChecked():
            # After reaching setpoint, check stability
            self.meas_status_update.emit('Beginning temperature stability check at {temp}...'
                                         .format(temp=self.step_temp))
            self.parent.enable_live_plots = False

            # Blocking loop for temperature equilibration
            count = 0
            start_time = time()
            for i in range(0, int(self.parent.dwell * 60)):
                if count % self.parent.stab_int == 0:
                    user_T.append(self.parent.sun.get_user_temp())
                    sleep(0.05)
                    chamber_T.append(self.parent.sun.get_temp())
                    z.append(self.parent.lcr.get_data()[1])
                    if self.parent.radio_chamber_tc.isChecked():
                        self.parent.lbl_curr_temp.setText(str(chamber_T[-1]))
                    elif self.parent.radio_user_tc.isChecked():
                        self.parent.lbl_curr_temp.setText(str(user_T[-1]))
                count += 1
                time_left = str(timedelta(seconds=int(self.parent.dwell * 60) - i))
                self.meas_status_update.emit("Checking stability at {temp}. Time Remaining: {time}"
                                             .format(temp=self.step_temp,
                                                     time=time_left))
                sleep(0.93)
                if self.stop:
                    break
            if self.stop:
                return
            self.parent.enable_live_plots = True
            self.meas_status_update.emit('Temperature stability check was scheduled for '
                                         '{} s, and took {} s.'.format(self.parent.dwell * 60,
                                                                       time() - start_time))

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
                self.meas_status_update.emit(
                    'Temperature ({delta} vs {deltol}) or standard deviation ({stdev} vs {stdevtol}) '
                    'outside of tolerance.'.format(delta=abs(self.chamber_avg - self.step_temp), deltol=temp_tol,
                                                   stdev=self.chamber_stdev, stdevtol=stdev_tol))
                sleep(2)
                self.blocking_func()
            # print('Temperature readings within tolerance')
            if self.parent.check_z_stability.isChecked():
                if self.z_stdev > z_stdev_tol:
                    self.meas_status_update.emit(
                        'Impedance variation outside of tolerance: Tolerance={tol}, Measured Stdev={stdev}'
                            .format(tol=z_stdev_tol, stdev=self.z_stdev))
                    sleep(2)
                    self.blocking_func()
                # print('Impedance stability within tolerance.')

        # Add the standard measurement delay from cap freq
        super().blocking_func()

        # trigger measurement on the SP-200
        self.parent.sun.set_analog_output(0, 255)
        sleep(0.25)
        self.parent.sun.set_analog_output(0, 0)
        # Sleep through most of the measurement
        sleep(6*60)
        # Check every quarter second to see if the SP-200 has set the complete trigger to high
        while(self.parent.sun.read_analog_input(0, 0) < 18000):
            sleep(0.25)
            print("Tested trigger out value")
        print("Saw High value on trigger out pin, moving on.")


if __name__ == "__main__":
    lcr = AgilentE4980A(parent=None)
    sun = SunEC1xChamber(parent=None, gpib_addr='GPIB0::6::INSTR')
    app = QApplication(sys.argv)
    main_window = CapFreqTempWidget(lcr=lcr, sun=sun)
    main_window.show()
    sys.exit(app.exec_())
