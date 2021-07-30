import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from time import sleep
from time import time

import numpy as np
import pandas as pd
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QTableWidgetItem, QTabWidget, QMessageBox, QApplication,
                             QFileDialog, QPushButton, QShortcut)
from pyvisa.errors import VisaIOError

import Static_Functions as Static
from File_Print_Headers import CAP_FREQ_HEADER, CAP_FREQ_TEMP_ADDON
# Can be used to emulate the LCR without connection data will be garbage (random numbers)
# from fake_E4980 import AgilentE4980A
from Instrument_Interfaces import Agilent_E4980A_Constants as Const
from Instrument_Interfaces.Agilent_E4980A import AgilentE4980A
from Instrument_Interfaces.HotplateRobot import HotplateRobot
from Instrument_Interfaces.Sun_EC1X import SunEC1xChamber
from src.ui.cap_freq_temp_tabs import Ui_cap_freq


class CapFreqWidget(QTabWidget):
    # This signal needs to be defined before the __init__ in order to allow it to work
    stop_measurement_worker = pyqtSignal()
    start_measuring = pyqtSignal()

    def __init__(self, lcr: AgilentE4980A, sun: SunEC1xChamber or None, hotplate_robot: HotplateRobot,
                 measuring_thread=QThread()):
        super(CapFreqWidget, self).__init__()
        # Define instruments/peripherals
        self.lcr = lcr
        self.sun = sun
        self.hotplate_robot = hotplate_robot
        # Dictionary of references to temperature control devices
        self.temp_control_devices = {"None": None, 'Sun EC1A': self.sun, 'Hotplate Robot': self.hotplate_robot}
        self.current_temp_control_device = 'None'

        # ToDo: Continue Here
        self.lcr_function = None  # Dummy value which is set after connection
        self.measuring_time = 'long'
        self.range = 'auto'
        self.data_averaging = 1
        self.signal_type = 'voltage'
        self.bias_type = 'voltage'
        self.num_pts = 50
        self.pre_meas_delay = 0.0
        self.enable_live_plots = False
        self.enable_live_vals = True
        # Variables for storing temperature control settings
        self.dwell = 10
        self.ramp = 5
        self.stab_int = 5
        self.temp_tol = 0.5
        self.stdev_tol = 0.5
        self.z_stdev_tol = 1000

        self.num_measurements = 1
        self.tests_df = pd.DataFrame()
        self.data_dict = {}
        self.header_dict = {}
        self.save_file_path = os.path.join(os.getenv('USERPROFILE'), 'Desktop')

        # Pull in measuring thread and initialize worker object
        self.measuring_thread = measuring_thread

        # Tiny bit of initial instrument setup
        self.lcr.dc_bias_state('on')
        self.return_to_defaults()

        # Load PyUI information and run setupUi function to build layout
        self.ui = Ui_cap_freq()
        self.ui.setupUi(self)

        # Define controls for the per measurement settings
        # self.meas_setup_hheaders = ['Frequency Start [Hz]',
        #                             'Frequency Stop [Hz]',
        #                             'Oscillator [V]',
        #                             'DC Bias [V]',
        #                             'Equilibration Delay [s]']
        self.meas_setup_vheaders = ['M1']
        # DONE: Reinitialize table headers based on what temperature control device is selected.
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Equilibration Delay [s]',
                                    'Temperature Set Point [°C]']
        # This might break depending on how adding headers to a table is handled in pyqt5
        # FIXME: Update calls to temperature UI parts in copied code.
        # FIXME: Add greyed out gbox for temp control if no temperature control device selected

        self.init_measure_worker()

        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()
        self.live_readout_timer = QTimer()
        self.ui.btn_run_start_stop = self.findChild(QPushButton, 'btn_run_start_stop')
        self.ui.btn_setup_start_stop = self.findChild(QPushButton, 'btn_setup_start_stop')

        # Set up for allowing copy paste in the measurement table
        self.clipboard = QApplication.clipboard()
        self.copy_sc = QShortcut(QKeySequence('Ctrl+C'), self.ui.table_meas_setup, self.copy_table, self.copy_table)
        self.paste_sc = QShortcut(QKeySequence('Ctrl+V'), self.ui.table_meas_setup, self.paste_table, self.paste_table)

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()

    def init_connections(self):
        # Control edit connections
        self.ui.combo_function.currentTextChanged.connect(self.change_function)
        self.ui.combo_meas_time.currentTextChanged.connect(self.change_meas_aperture)
        self.ui.ln_data_averaging.editingFinished.connect(self.change_meas_aperture)
        self.ui.ln_num_pts.editingFinished.connect(self.change_num_pts)
        self.ui.ln_pre_meas_delay.editingFinished.connect(self.change_pre_meas_delay)
        self.ui.combo_range.currentTextChanged.connect(self.change_impedance_range)
        self.ui.combo_signal_type.currentTextChanged.connect(self.change_signal_type)
        self.ui.combo_bias_type.currentTextChanged.connect(self.change_bias_type)
        self.ui.ln_save_file.editingFinished.connect(self.set_save_file_path_by_line)
        self.ui.btn_save_file.clicked.connect(self.set_save_file_path_by_dialog)
        self.ui.ln_num_meas.editingFinished.connect(self.change_num_measurements)
        self.ui.btn_copy_table.clicked.connect(self.copy_table)
        self.ui.btn_paste_table.clicked.connect(self.paste_table)
        self.ui.btn_run_start_stop.clicked.connect(self.on_start_stop_clicked)
        self.ui.btn_setup_start_stop.clicked.connect(self.on_start_stop_clicked)
        # Add connections for temperature controls
        self.ui.combo_temp_control.currentTextChanged.connect(self.change_temp_control_device)
        self.ui.ln_dwell.editingFinished.connect(self.change_dwell)
        self.ui.ln_ramp.editingFinished.connect(self.change_ramp)
        self.ui.ln_stab_int.editingFinished.connect(self.change_stab_int)
        self.ui.ln_temp_tol.editingFinished.connect(self.change_temp_tol)
        self.ui.ln_stdev_tol.editingFinished.connect(self.change_stdev_tol)
        self.ui.ln_z_stdev_tol.editingFinished.connect(self.change_z_stdev_tol)

        # Timers
        self.live_readout_timer.timeout.connect(self.get_new_data)
        self.lcr.new_data.connect(self.update_live_readout)
        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()

        # Cross thread communication
        self.measuring_worker.measurement_finished.connect(self.measuring_thread.quit)
        self.stop_measurement_worker.connect(self.measuring_worker.stop_early)
        self.measuring_worker.freq_step_finished.connect(self.update_measurement_progress)
        self.measuring_thread.finished.connect(self.end_measurement)
        self.measuring_thread.started.connect(self.measuring_worker.measure)
        self.lcr.new_data.connect(self.plot_new_points)
        self.measuring_worker.meas_status_update.connect(self.update_meas_status)

    def init_measure_worker(self):
        # DONE: Consolidate measure workers into one object
        self.measuring_worker = CapFreqMeasureWorkerObject(self)
        self.measuring_worker.moveToThread(self.measuring_thread)
        self.move_instr_to_worker_thread()

    def init_control_setup(self):
        self.init_setup_table()

        # Set up comboboxes
        self.ui.combo_range.addItems(Const.VALID_IMP_RANGES)
        self.ui.combo_function.addItems(list(Const.FUNC_DICT.keys()))
        self.ui.combo_meas_time.addItems(list(Const.MEASURE_TIME_DICT.keys()))
        self.ui.combo_signal_type.addItems(['Voltage', 'Current'])
        self.ui.combo_bias_type.addItems(['Voltage', 'Current'])

        # Add default values for fields
        self.ui.ln_num_pts.setText(str(self.num_pts))
        self.ui.ln_data_averaging.setText(str(self.data_averaging))
        self.ui.ln_pre_meas_delay.setText(str(self.pre_meas_delay))

        # Add available temperature control devices to the drop down
        # FIXME: 2 Add checking that each device is online and adjust this list accordingly.
        # FIXME: 2 Add a way to reconnect to devices while GUI is running
        self.ui.combo_temp_control.addItems(list(self.temp_control_devices.keys()))
        self.ui.combo_temp_control.setCurrentText(self.current_temp_control_device)
        self.ui.ln_dwell.setText(str(self.dwell))
        self.ui.ln_ramp.setText(str(self.ramp))
        self.ui.ln_stab_int.setText(str(self.stab_int))
        self.ui.ln_temp_tol.setText(str(self.temp_tol))
        self.ui.ln_stdev_tol.setText(str(self.stdev_tol))
        self.ui.ln_z_stdev_tol.setText(str(self.z_stdev_tol))

        # Set the initial values for dwell, ramprate, and stability interval
        self.change_dwell()
        self.change_ramp()
        self.change_stab_int()

        # Set up timers
        self.live_readout_timer.start(500)

    def init_setup_table(self):
        # Set up initial table headers and size
        self.ui.table_meas_setup.setRowCount(len(self.meas_setup_vheaders))
        self.ui.table_meas_setup.setColumnCount(5)
        self.ui.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.ui.table_meas_setup.setVerticalHeaderLabels(self.meas_setup_vheaders)
        self.ui.table_meas_setup.setWordWrap(True)
        self.add_table_items()

        self.ui.table_meas_setup.item(0, 0).setText('20')
        self.ui.table_meas_setup.item(0, 1).setText('2000000')
        self.ui.table_meas_setup.item(0, 2).setText('0.2')
        self.ui.table_meas_setup.item(0, 3).setText('0')
        self.ui.table_meas_setup.item(0, 4).setText('0')

        # DONE: Reinitialize table headers based on what temperature control device is selected.
        if self.current_temp_control_device != "None":
            print("It Ran")
            self.ui.table_meas_setup.setColumnCount(6)
            self.ui.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)
            self.add_table_items()
            self.ui.table_meas_setup.item(0, 5).setText('35')

        self.ui.table_meas_setup.resizeColumnsToContents()

    def get_new_data(self):
        # Helper function to get new data on timer timeout. Was failing when called directly, could be something about
        #  having a return value?
        if self.enable_live_vals:
            self.lcr.get_data()

    def change_function(self):
        self.lcr_function = self.ui.combo_function.currentText()
        self.update_val_labels()

    def change_meas_aperture(self):
        self.measuring_time = self.ui.combo_meas_time.currentText()
        try:
            self.data_averaging = int(self.ui.ln_data_averaging.text())
        except ValueError:
            self.data_averaging = 1
            self.ui.ln_data_averaging.setText(str(self.data_averaging))

    def change_num_pts(self):
        try:
            self.num_pts = int(self.ui.ln_num_pts.text())
        except ValueError:
            self.num_pts = 50
            self.ui.ln_num_pts.setText(str(self.num_pts))

    def change_pre_meas_delay(self):
        try:
            self.pre_meas_delay = float(self.ui.ln_pre_meas_delay.text())
        except ValueError:
            self.pre_meas_delay = 0.0
        self.ui.ln_pre_meas_delay.setText(str(self.pre_meas_delay))

    def change_impedance_range(self):
        self.range = self.ui.combo_range.currentText()

    def change_signal_type(self):
        self.signal_type = self.ui.combo_signal_type.currentText()

    def change_bias_type(self):
        self.bias_type = self.ui.combo_bias_type.currentText()

    def change_temp_control_device(self, current_text: str):
        self.current_temp_control_device = current_text
        self.init_setup_table()
        if current_text == "None":
            self.ui.gbox_thermal_settings.setDisabled(True)
            self.ui.gbox_curr_temp.hide()
            self.ui.lbl_pipe4.hide()
            self.ui.lbl_temp.hide()
            self.ui.lbl_curr_meas_temp.hide()
        else:
            self.ui.gbox_thermal_settings.setDisabled(False)
            self.ui.gbox_curr_temp.show()
            self.ui.lbl_pipe4.show()
            self.ui.lbl_temp.show()
            self.ui.lbl_curr_meas_temp.show()
            self.ui.vlayout_current_vals.setStretchFactor(self.ui.gbox_curr_temp, 5)
            if self.current_temp_control_device == 'Sun EC1A':
                self.ui.hlayout_temp_channel.show()
                self.ui.lbl_ramp.setText("Ramp Rate:")
            elif self.current_temp_control_device == 'Hotplate Robot':
                self.ui.hlayout_temp_channel.hide()
                self.ui.lbl_ramp.setText("Ramp Time:")

    def change_dwell(self):
        self.dwell = float(self.ui.ln_dwell.text())

    def change_temp_tol(self):
        self.temp_tol = float(self.ui.ln_temp_tol.text())

    def change_stdev_tol(self):
        self.stdev_tol = float(self.ui.ln_stdev_tol.text())

    def change_z_stdev_tol(self):
        self.z_stdev_tol = float(self.ui.ln_z_stdev_tol.text())

    def change_ramp(self):
        self.ramp = float(self.ui.ln_ramp.text())

    def change_stab_int(self):
        self.stab_int = float(self.ui.ln_stab_int.text())

    def set_save_file_path_by_dialog(self):
        file_name = QFileDialog.getSaveFileName(self,
                                                'Select a file to save data...',
                                                self.save_file_path,
                                                "Dat Files (*.dat);;xy Files (*.xy);;All Types (*.*)",
                                                options=QFileDialog.DontConfirmOverwrite)
        self.save_file_path = file_name[0]
        if not os.path.exists(os.path.dirname(os.path.abspath(self.save_file_path))):
            try:
                os.mkdir(os.path.dirname(os.path.abspath(self.save_file_path)))
            except PermissionError:
                permission_denied = QMessageBox.warning(self, 'Permission Denied',
                                                        'Permission to create the specified folder was denied. \
                                                        Please pick another location to save your data',
                                                        QMessageBox.OK, QMessageBox.Ok)
                if permission_denied == QMessageBox.Ok:
                    self.set_save_file_path_by_dialog()

        self.ui.ln_save_file.setText(self.save_file_path)

    def set_save_file_path_by_line(self):
        if self.ui.ln_save_file.text() != '':
            self.save_file_path = self.ui.ln_save_file.text()

    def change_num_measurements(self):
        num = self.num_measurements
        try:
            self.num_measurements = int(self.ui.ln_num_meas.text())
        except ValueError:
            self.num_measurements = num

        self.ui.table_meas_setup.setRowCount(self.num_measurements)
        self.update_table_vheaders()
        self.add_table_items()

    def update_live_readout(self, data: list):
        self.ui.lbl_curr_freq.setText(str(Static.si_prefix(data[0], 'Hz', 4)))
        self.ui.lbl_val1.setText(str(Static.to_sigfigs(data[1], 6)))
        self.ui.lbl_val2.setText(str(Static.to_sigfigs(data[2], 6)))

        if self.enable_live_vals:
            try:
                if self.ui.radio_chamber_tc.isChecked():
                    self.ui.lbl_curr_temp.setText(str(self.sun.get_temp()))
                elif self.ui.radio_user_tc.isChecked():
                    self.ui.lbl_curr_temp.setText(str(self.sun.get_user_temp()))
            except VisaIOError:
                print('Error on getting temperature from sun chamber')

    def update_table_hheaders(self):
        self.ui.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)

    def update_table_vheaders(self):
        self.meas_setup_vheaders = ['M{}'.format(x) for x in range(1, self.num_measurements + 1)]
        self.ui.table_meas_setup.setVerticalHeaderLabels(self.meas_setup_vheaders)

    def add_table_items(self):
        for irow in range(0, self.ui.table_meas_setup.rowCount()):
            for icol in range(0, self.ui.table_meas_setup.columnCount()):
                widget = self.ui.table_meas_setup.item(irow, icol)
                # If the cell doesn't already have a QTableWidgetItem
                if widget is None:
                    # Create a new QTableWidgetItem in the cell
                    new_widget = QTableWidgetItem()
                    if irow > 0:
                        # Get the value of the cell above
                        value = self.ui.table_meas_setup.item(irow - 1, icol).text()
                        new_widget.setText(value)
                    # Put the new widget in the table
                    self.ui.table_meas_setup.setItem(irow, icol, new_widget)

    def copy_table(self):
        tmprow = ''
        copystr = ''

        for irow in range(0, self.ui.table_meas_setup.rowCount()):
            for icol in range(0, self.ui.table_meas_setup.columnCount()):
                tmprow = tmprow + self.ui.table_meas_setup.item(irow, icol).text() + '\t'

            copystr = copystr + tmprow.rstrip('\t') + '\n'
            tmprow = ''

        self.clipboard.setText(copystr)

    def paste_table(self):
        rows = self.clipboard.text().split('\n')[:-1]

        self.num_measurements = len(rows)
        self.ui.ln_num_meas.setText(str(len(rows)))
        self.change_num_measurements()

        for (irow, row_val) in enumerate(rows):
            tmpcols = row_val.split('\t')
            for (icol, col_val) in enumerate(tmpcols):
                self.ui.table_meas_setup.item(irow, icol).setText(str(col_val))

    def generate_header(self, index, row):
        header_vars = self.get_header_vars(index, row)

        header = CAP_FREQ_HEADER.format(meas_type=self.lcr_function,
                                        meas_date=header_vars['date_now'],
                                        meas_time=header_vars['time_now'],
                                        meas_num=header_vars['meas_number'],
                                        start_freq=header_vars['start'],
                                        stop_freq=header_vars['stop'],
                                        range=self.range,
                                        num_pts=self.num_pts,
                                        data_averaging=self.data_averaging,
                                        step_delay=header_vars['step_delay'],
                                        osc_type=header_vars['osc_type'],
                                        osc=header_vars['osc'],
                                        bias_type=header_vars['bias_type'],
                                        bias=header_vars['bias'],
                                        pre_meas_delay=self.pre_meas_delay,
                                        notes='Notes:\t{}'.format(header_vars['notes']))

        # DONE: Handle cases where there is no temp control device and don't temp data to
        #  headers
        if self.current_temp_control_device != 'None':
            if self.measuring_worker.step_temp == self.measuring_worker.prev_step_temp and not self.ui.check_always_stab.isChecked():
                user_avg = str(Static.to_sigfigs(self.measuring_worker.user_avg, 5)) + '*'
                user_stdev = str(Static.to_sigfigs(self.measuring_worker.user_stdev, 5)) + '*'
                chamber_avg = str(Static.to_sigfigs(self.measuring_worker.chamber_avg, 5)) + '*'
                chamber_stdev = str(Static.to_sigfigs(self.measuring_worker.chamber_stdev, 5)) + '*'
                z_stdev = str(Static.to_sigfigs(self.measuring_worker.z_stdev, 5)) + '*'
            else:
                user_avg = str(Static.to_sigfigs(self.measuring_worker.user_avg, 5))
                user_stdev = str(Static.to_sigfigs(self.measuring_worker.user_stdev, 5))
                chamber_avg = str(Static.to_sigfigs(self.measuring_worker.chamber_avg, 5))
                chamber_stdev = str(Static.to_sigfigs(self.measuring_worker.chamber_stdev, 5))
                z_stdev = str(Static.to_sigfigs(self.measuring_worker.z_stdev, 5))

            # Replace the separator for the sample notes with the thermal information + the separator for
            #  sample notes.
            header = header.replace('\n***********Sample Notes***********',
                                    CAP_FREQ_TEMP_ADDON.format(temp_device=header_vars['temp_device'],
                                                               ramp=header_vars['ramp'],
                                                               dwell=header_vars['dwell'],
                                                               stab_int=header_vars['stab_int'],
                                                               user_avg=user_avg,
                                                               user_stdev=user_stdev,
                                                               chamber_avg=chamber_avg,
                                                               chamber_stdev=chamber_stdev,
                                                               z_stdev=z_stdev, ))
            if self.current_temp_control_device == 'Hotplate Robot':
                header.replace('\nRamp Rate:\t', '\nRamp Time:\t')

        return header

    def get_header_vars(self, index, row):
        # Gather format strings for header
        header_vars = {'meas_number': index}
        now = datetime.now()
        header_vars['date_now'] = str(now).split(' ')[0]
        header_vars['time_now'] = str(now.strftime('%H:%M:%S'))

        header_vars['start'] = row[self.meas_setup_hheaders[0]]
        header_vars['stop'] = row[self.meas_setup_hheaders[1]]

        header_vars['osc'] = row[self.meas_setup_hheaders[2]]
        if self.ui.combo_signal_type.currentText() == 'Voltage':
            header_vars['osc_type'] = 'V'
        elif self.ui.combo_signal_type.currentText() == 'Current':
            header_vars['osc_type'] = 'A'
        else:
            header_vars['osc_type'] = 'UNKNOWN'

        header_vars['bias'] = row[self.meas_setup_hheaders[3]]
        if self.ui.combo_bias_type.currentText() == 'Voltage':
            header_vars['bias_type'] = 'V'
        elif self.ui.combo_bias_type.currentText() == 'Current':
            header_vars['bias_type'] = 'A'
        else:
            header_vars['bias_type'] = 'UNKNOWN'

        header_vars['step_delay'] = row[self.meas_setup_hheaders[4]]
        header_vars['notes'] = self.ui.ln_notes.text()

        # DONE: Handle cases where there is no temp control device and don't temp data to
        #  headers
        if self.current_temp_control_device != 'None':
            header_vars['temp_device'] = self.current_temp_control_device
            header_vars['ramp'] = self.ramp
            header_vars['dwell'] = self.dwell
            header_vars['stab_int'] = self.stab_int

        return header_vars

    def generate_test_matrix(self):
        self.tests_df = pd.DataFrame(data=None, index=self.meas_setup_vheaders, columns=self.meas_setup_hheaders)

        for irow in range(0, self.ui.table_meas_setup.rowCount()):
            for icol in range(0, self.ui.table_meas_setup.columnCount()):
                self.tests_df.iloc[irow, icol] = self.ui.table_meas_setup.item(irow, icol).text()

    def enable_controls(self, enable: bool):
        self.ui.gbox_meas_setup.setEnabled(enable)
        self.ui.gbox_meas_set_params.setEnabled(enable)
        # FIXME: Does this need to be context dependent? Maybe only for enable.
        self.ui.gbox_thermal_settings.setEnabled(enable)

    def setup_lcr(self):
        self.lcr.function(self.lcr_function)
        self.lcr.impedance_range(self.range)
        self.lcr.measurement_aperture(self.measuring_time, self.data_averaging)
        self.lcr.signal_level(self.signal_type, self.ui.table_meas_setup.item(0, 2).text())
        self.lcr.dc_bias_level(self.bias_type, self.ui.table_meas_setup.item(0, 3).text())

    def on_start_stop_clicked(self):
        # Get the sender
        btn = self.sender()
        # If the sender is checked (trying to start the measurement)
        if btn.isChecked():
            # Set both buttons to checked
            self.ui.btn_setup_start_stop.setChecked(True)
            self.ui.btn_run_start_stop.setChecked(True)
            # Pause the update timer
            self.enable_live_vals = False
            # Set the text on both buttons
            self.ui.btn_setup_start_stop.setText('Stop Measurements')
            self.ui.btn_run_start_stop.setText('Stop Measurements')
            # Start the measurement
            self.start_measurement()
        # If the sender is not checked (User has cancelled measurement)po0909o0poi9o
        elif not btn.isChecked():
            # Set both buttons to unchecked
            self.ui.btn_setup_start_stop.setChecked(False)
            self.ui.btn_run_start_stop.setChecked(False)
            # Enable the update timer
            self.enable_live_vals = True
            # Set the text on both buttons
            self.ui.btn_setup_start_stop.setText('Run Measurement Set')
            self.ui.btn_run_start_stop.setText('Run Measurement Set')
            # Start the measurement
            self.halt_measurement()

    def move_instr_to_worker_thread(self):
        self.lcr.moveToThread(self.measuring_thread)
        self.sun.moveToThread(self.measuring_thread)

    def halt_measurement(self):
        self.stop_measurement_worker.emit()
        self.enable_live_plots = False
        self.enable_live_vals = True
        self.enable_controls(True)

    def start_measurement(self):
        self.set_save_file_path_by_line()
        self.check_file_path()

        self.setCurrentWidget(self.ui.tab_run_meas)
        # Set up the progress bar for this measurement
        self.ui.progress_bar_meas.setMinimum(0)
        self.ui.progress_bar_meas.setMaximum(self.num_measurements * self.num_pts)
        self.ui.progress_bar_meas.reset()
        # Keep the user from changing values in the controls
        self.enable_controls(False)
        # Set live vals to update to last read value only
        self.enable_live_vals = False
        # Enable live plotting of values, clear previous data
        self.ui.live_plot.clear_data()
        self.enable_live_plots = True

        self.move_instr_to_worker_thread()
        # Emit signal to start the worker measuring
        self.measuring_thread.start()

    def dep_cancelled_by_user(self):
        cancel = QMessageBox.information(self, 'Measurement canceled',
                                         'Measurement cancelled by user.',
                                         QMessageBox.Ok, QMessageBox.Ok)
        if cancel == QMessageBox.Ok:
            self.ui.btn_setup_start_stop.setChecked(False)
            self.ui.btn_run_start_stop.setChecked(False)
            self.halt_measurement()
            return

    def check_file_path(self):
        if os.path.isfile(self.save_file_path):
            overwrite = QMessageBox.warning(self, 'File already exists',
                                            'This data file already exists. Would you like to overwrite?',
                                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                            QMessageBox.No)
            if overwrite == QMessageBox.No:
                self.set_save_file_path_by_dialog()
                self.start_measurement()
            elif overwrite == QMessageBox.Cancel:
                self.dep_cancelled_by_user()
                return
        elif self.save_file_path == os.path.join(os.getenv('USERPROFILE'), 'Desktop') or self.save_file_path == '':
            no_file_selected = QMessageBox.warning(self, 'No File Selected',
                                                   'No file has been selected for writing data, '
                                                   'please pick a file to save to.',
                                                   QMessageBox.Ok | QMessageBox.Cancel,
                                                   QMessageBox.Ok)
            if no_file_selected == QMessageBox.Ok:
                self.set_save_file_path_by_dialog()
                self.start_measurement()
            elif no_file_selected == QMessageBox.Cancel:
                self.dep_cancelled_by_user()
                return
            # Fixme: maybe add more file save path checking i.e. blank or default location.

    # When the worker says it is done, save data and reset widget state to interactive
    def end_measurement(self):
        # Enable the user to change controls
        self.enable_controls(True)
        # Set live vals to update periodically
        self.enable_live_vals = True
        # Disable live plotting of values
        self.enable_live_plots = False
        self.return_to_defaults()

        # print('Measurement finished')
        # Change start/stop button back to start
        # Set both buttons to unchecked
        self.ui.btn_setup_start_stop.setChecked(False)
        self.ui.btn_run_start_stop.setChecked(False)
        # Set the text on both buttons
        self.ui.btn_setup_start_stop.setText('Start Measurements')
        self.ui.btn_run_start_stop.setText('Start Measurements')

    def return_to_defaults(self):
        # print('Returning lcr to defaults')
        self.lcr.dc_bias_level('voltage', 0)
        self.lcr.signal_level('voltage', 0.05)
        self.lcr.signal_frequency(1000)

    def save_data(self):
        with open(self.save_file_path, 'w') as file:
            for key in self.header_dict:
                ram_csv = StringIO()
                file.write(self.header_dict[key])
                self.data_dict[key].to_csv(ram_csv,
                                           sep='\t', index_label='idx')
                file.write(ram_csv.getvalue())
                file.write('\n*************End Data*************\n\n')
                ram_csv.close()

    def plot_new_points(self, data: list):
        if self.enable_live_plots:
            # Handle data that is fed to the plot for special cases.
            if self.lcr_function == 'Z-Thd':
                zreal = data[1] * np.cos(np.deg2rad(data[2]))
                zimag = data[1] * np.sin(np.deg2rad(data[2]))
                self.ui.live_plot.add_data([zreal, -1 * zimag])
            else:
                self.ui.live_plot.add_data([data[0], data[1], data[2]])

    def update_val_labels(self):
        # Get the two parameters that are being measured/output
        val_params = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.lcr_function]]

        # Handle special cases for the live plot
        if self.lcr_function == 'Z-Thd':
            self.ui.live_plot.canvas.set_dual_y(False, ["Z' (Ohm)", "-Z'' (Ohm)"])
        else:
            self.ui.live_plot.canvas.set_dual_y(True, ['Frequency [Hz]', val_params[0], val_params[1]])

        # Set the live value readout names regardless
        self.ui.gbox_val1.setTitle(val_params[0])
        self.ui.gbox_val2.setTitle(val_params[1])

    def update_measurement_progress(self, indices: list):
        # NOTE: indices[0] will be the measurement number (one indexed), and
        # indices[1] will be the step number (Zero indexed)
        self.ui.progress_bar_meas.setValue(((indices[0] - 1) * self.num_pts) + (indices[1] + 1))
        self.ui.lbl_meas_progress.setText('Measurement {}/{},\nStep {}/{}'.format(indices[0], self.num_measurements,
                                                                                  indices[1] + 1, self.num_pts))

    def update_meas_status(self, update_str: str):
        self.ui.lbl_meas_status.setText(update_str)


class CapFreqMeasureWorkerObject(QObject):
    measurement_finished = pyqtSignal()
    freq_step_finished = pyqtSignal(list)
    meas_status_update = pyqtSignal(str)

    def __init__(self, parent: CapFreqWidget):
        super(CapFreqMeasureWorkerObject, self).__init__()
        self.parent = parent
        self.stop = False
        self.data_df = pd.DataFrame()
        self.parent.stop_measurement_worker.connect(self.stop_early)
        # ProbeStationControlMainWindow.active_measurement_changed.connect(self.return_instr_to_main_thread)

        # Predefine class variables
        self.step_start = 0
        self.step_stop = 0
        self.step_osc = 0
        self.step_bias = 0
        self.step_delay = 0

        # Define temperature control variables
        self.step_temp = None
        self.user_avg = 0
        self.chamber_avg = 0
        self.user_stdev = 0
        self.chamber_stdev = 0
        self.z_stdev = 0
        self.prev_step_temp = None

    def stop_early(self):
        self.stop = True

    def set_current_meas_labels(self):
        self.parent.ui.lbl_curr_meas_start.setText(str(self.step_start))
        self.parent.ui.lbl_curr_meas_stop.setText(str(self.step_stop))
        self.parent.ui.lbl_curr_meas_osc.setText(str(self.step_osc))
        self.parent.ui.lbl_curr_meas_bias.setText(str(self.step_bias))

        # FIXME: only if temperature control device is not None --> Actually will be hidden so we don't care as long
        #  as it doesn't crash
        self.parent.ui.lbl_curr_meas_temp.setText(str(self.step_temp))

    def set_test_params(self, row):
        # Set up current test specific values
        self.step_start = row[self.parent.meas_setup_hheaders[0]]
        self.step_stop = row[self.parent.meas_setup_hheaders[1]]
        self.step_osc = row[self.parent.meas_setup_hheaders[2]]
        self.step_bias = row[self.parent.meas_setup_hheaders[3]]
        self.step_delay = float(row[self.parent.meas_setup_hheaders[4]])

        # DONE: only if temperature control device is not None
        if self.parent.current_temp_control_device != "None":
            self.prev_step_temp = self.step_temp
            self.step_temp = float(row[self.parent.meas_setup_hheaders[5]])

    def get_out_columns(self):
        columns = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.parent.ui.combo_function.currentText()]]
        if columns[0] != 'Frequency [Hz]':
            columns.insert(0, 'Frequency [Hz]')

        return columns

    def read_new_data(self):
        # Read the measurement result
        data = self.parent.lcr.get_data()
        data = pd.Series(data, index=self.data_df.columns)

        # Store the data to the data_df
        self.data_df = self.data_df.append(data, ignore_index=True)

    def blocking_func(self):
        # DONE: Behavior based on selected temperature control device.
        if self.parent.current_temp_control_device == "None":
            pass
        else:
            # Define variables to hold logged temperatures
            user_T = []
            chamber_T = []
            z = []

            if self.step_temp != self.prev_step_temp:
                # Send the command to change the temperature
                # FIXME: 2 Change all branches of this type to be less manual if possible.
                if self.parent.current_temp_control_device == 'Sun EC1A':
                    self.parent.sun.set_setpoint(self.step_temp)
                    device = 'chamber'
                elif self.parent.current_temp_control_device == 'Hotplate Robot':
                    self.parent.hotplate_robot.set_setpoint(self.step_temp)
                    device = 'hotplate'
                self.meas_status_update.emit("Waiting for {} to reach {}...".format(device, self.step_temp))

                if self.parent.current_temp_control_device == 'Sun EC1A':
                    # Get the current temperature and loop until setpoint is achieved
                    check_temp = float(self.parent.sun.get_temp())
                    if self.step_temp > check_temp:
                        while check_temp < self.step_temp - self.parent.temp_tol:
                            check_temp = float(self.parent.sun.get_temp())
                            self.parent.ui.lbl_curr_temp.setText(str(check_temp))
                            sleep(1)
                            if self.stop:
                                break
                    elif self.step_temp < check_temp:
                        while check_temp > self.step_temp + self.parent.temp_tol:
                            check_temp = float(self.parent.sun.get_temp())
                            self.parent.ui.lbl_curr_temp.setText(str(check_temp))
                            sleep(1)
                            if self.stop:
                                break
                elif self.parent.current_temp_control_device == 'Hotplate Robot':
                    # Use a running average of last 60 seconds to determine if heating has finished + temperature
                    #  is stabilizing.
                    count = 0
                    while True:
                        chamber_T = chamber_T[-60:]
                        chamber_T.append(float(self.parent.hotplate_robot.get_temp()))
                        self.parent.ui.lbl_curr_temp.setText(chamber_T[-1])
                        count += 1
                        sleep(1)
                        if count >= int(self.parent.ui.ln_ramp.text()) * 60:
                            print("Hotplate ramp time complete. "
                                  "Temperature standard deviation = {}".format(np.std(chamber_T)))
                            if np.std(chamber_T) < self.parent.stdev_tol:
                                chamber_T = []
                                break
                        if self.stop:
                            break

            if self.step_temp != self.prev_step_temp or self.parent.ui.check_always_stab.isChecked():
                # After reaching setpoint, check stability
                self.meas_status_update.emit('Beginning temperature stability check at {temp}...'
                                             .format(temp=self.step_temp))
                self.parent.enable_live_plots = False

                # Blocking loop for temperature equilibration
                count = 0
                start_time = time()
                for i in range(0, int(self.parent.dwell * 60)):
                    if count % self.parent.stab_int == 0:
                        if self.parent.current_temp_control_device == 'Sun EC1A':
                            user_T.append(self.parent.sun.get_user_temp())
                            sleep(0.05)
                            chamber_T.append(self.parent.sun.get_temp())
                        elif self.parent.current_temp_control_device == 'Hotplate Robot':
                            chamber_T.append(self.parent.hotplate_robot.get_temp())
                            sleep(0.05)
                        z.append(self.parent.lcr.get_data()[1])
                        if self.parent.ui.radio_chamber_tc.isChecked() or self.parent.current_temp_control_device == 'Hotplate Robot':
                            self.parent.ui.lbl_curr_temp.setText(str(chamber_T[-1]))
                        elif self.parent.ui.radio_user_tc.isChecked():
                            self.parent.ui.lbl_curr_temp.setText(str(user_T[-1]))
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

                # Calculate temperature statistics
                self.user_avg = np.mean(user_T)
                self.user_stdev = np.std(user_T)
                self.chamber_avg = np.mean(chamber_T)
                self.chamber_stdev = np.std(chamber_T)
                self.z_stdev = np.std(z)

                # Check that statistics are within user specification. Re-run equilibration if so.
                in_spec = True
                if self.parent.current_temp_control_device == 'Sun EC1A' and abs(
                        self.chamber_avg - self.step_temp) > self.parent.temp_tol:
                    self.meas_status_update.emit(
                        'Temperature too far from setpoint ({delta} vs {deltol}) outside of tolerance.'.format(
                            delta=abs(self.chamber_avg - self.step_temp), deltol=self.parent.temp_tol))
                    in_spec = False
                elif self.chamber_stdev > self.parent.stdev_tol:
                    self.meas_status_update.emit(
                        'Temperature unstable. Standard deviation ({stdev} vs {stdevtol}) outside of tolerance.'.format(
                            stdev=self.chamber_stdev, stdevtol=self.parent.stdev_tol))
                    in_spec = False
                if self.parent.ui.check_z_stability.isChecked():
                    if self.z_stdev > self.parent.z_stdev_tol:
                        self.meas_status_update.emit('Impedance variation outside of tolerance: '
                                                     'Tolerance={tol}, Measured Stdev={stdev}'.format(tol=self.parent.z_stdev_tol,
                                                                                                      stdev=self.z_stdev))
                        in_spec = False

                if not in_spec:
                    sleep(2)
                    return self.blocking_func()

    def condition_equilibration_delay(self):
        count = 0
        while count < self.step_delay:
            time_left = str(timedelta(seconds=self.step_delay - count))
            self.meas_status_update.emit('Waiting for sample equilibration. Time Remaining: '
                                         '{}s'.format(time_left))
            sleep(1)
            count += 1

    def return_instr_to_main_thread(self):
        # FIXME: This shit shouldn't be necessary
        self.lcr.moveToThread(QApplication.instance().thread())
        # self.sun.moveToThread(QApplication.instance().thread())

    def measurement_cleanup(self):
        # DONE: Check for temperature control context
        if self.parent.current_temp_control_device == 'None':
            self.meas_status_update.emit('Measurement Finished.')
        else:
            if self.parent.ui.check_return_to_rt.isChecked():
                if self.parent.current_temp_control_device == 'Sun EC1A':
                    self.parent.sun.set_setpoint(25.0)
                elif self.parent.current_temp_control_device == 'Hotplate Robot':
                    self.parent.hotplate_robot.set_setpoint(25.0)
                self.meas_status_update.emit('Measurement Finished. Temperature set point: 25°C')
            else:
                self.meas_status_update.emit('Measurement Finished.')
            # Prevent issues with rollover from previous measurements.
            self.step_temp = None
            self.prev_step_temp = None

    def measure(self):
        self.meas_status_update.emit("Starting measurement.")
        # Write configured parameters to lcr
        self.parent.setup_lcr()

        # Generate the matrix of tests to run
        self.parent.generate_test_matrix()

        # Set up the data column headers
        columns = self.get_out_columns()

        # For each measurement in the test matrix
        for index, row in self.parent.tests_df.iterrows():
            # Create an empty data frame to hold results, Column Headers determined by measurement type
            self.data_df = pd.DataFrame(data=None, columns=columns)

            # Set test params for this measurement
            self.set_test_params(row)

            # Set the information labels to match this row
            self.set_current_meas_labels()

            # Wait for whatever blocking function is needed (just delay here, override for temp)
            #  Return instrument to defaults while waiting so no one kills their samples
            self.parent.return_to_defaults()
            self.blocking_func()

            # Set lcr according to step parameters
            self.parent.lcr.signal_level(self.parent.ui.combo_signal_type.currentText(), self.step_osc)
            self.parent.lcr.dc_bias_level(self.parent.ui.combo_bias_type.currentText(), self.step_bias)

            # Generate frequency points for measurement
            freq_steps = Static.generate_log_steps(int(self.step_start),
                                                   int(self.step_stop),
                                                   int(self.parent.num_pts))

            # Delay to allow sample to equilibrate at measurement parameters
            self.condition_equilibration_delay()

            # Start a new data line in each plot
            self.parent.ui.live_plot.canvas.start_new_line()

            self.meas_status_update.emit('Measurement in progress...')

            for step_idx in range(0, len(freq_steps)):
                # Set the lcr to the correct frequency
                self.parent.lcr.signal_frequency(freq_steps[step_idx])

                # Wait for measurement to stabilize (50ms to allow signal to stabilize + user set delay)
                sleep(self.parent.pre_meas_delay + 0.05)

                # Trigger the measurement to start
                self.parent.lcr.trigger_init()

                # Read data and store it to the dataframe
                self.read_new_data()

                # Emit signal to update progress bar
                self.freq_step_finished.emit([int(index.split('M')[-1]), step_idx])
                if self.stop:
                    break

            # Store the measurement data in a field of the tests_df
            self.parent.header_dict[index] = self.parent.generate_header(index, row)
            self.parent.data_dict[index] = self.data_df
            self.parent.save_data()
            if self.stop:
                break

        self.stop = False
        self.measurement_cleanup()
        self.measurement_finished.emit()


if __name__ == "__main__":
    # if standalone == 'capfreq':
    lcr_inst = AgilentE4980A()
    sun_inst = SunEC1xChamber(gpib_addr='GPIB0::6::INSTR')
    hotplate_robot_inst = HotplateRobot(port='COM3', baud=115200)
    app = QApplication(sys.argv)
    main_window = CapFreqWidget(lcr=lcr_inst, sun=sun_inst, hotplate_robot=hotplate_robot_inst)
    main_window.show()
    sys.exit(app.exec_())
