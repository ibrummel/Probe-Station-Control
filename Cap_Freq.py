import sys

from PyQt5 import uic
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QWidget, QComboBox, QLineEdit, QLabel, QGroupBox, QTableWidget,
                             QTableWidgetItem, QTabWidget, QMessageBox, QToolButton, QApplication,
                             QFileDialog, QProgressBar, QPushButton, QShortcut)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject
import os
from io import StringIO
from time import sleep
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from Live_Data_Plotter import LivePlotWidget
from Agilent_E4980A import AgilentE4980A
# Can be used to emulate the LCR without connection data will be garbage (random numbers)
# from fake_E4980 import AgilentE4980A
import Agilent_E4980A_Constants as Const
from File_Print_Headers import *
import Static_Functions as Static


class CapFreqWidget(QTabWidget):
    # This signal needs to be defined before the __init__ in order to allow it to work
    stop_measurement_worker = pyqtSignal()
    start_measuring = pyqtSignal()

    def __init__(self, lcr: AgilentE4980A, measuring_thread=QThread(), ui_path='./src/ui/cap_freq_tabs.ui'):
        super().__init__()
        # print('Initializing Capacitance-Frequency Widget...')
        # Define class variables and objects
        self.lcr = lcr
        self.lcr_function = 'self.lcr.get_current_function()'  # Dummy value which is set after connection
        self.measuring_time = 'long'
        self.range = 'auto'
        self.data_averaging = 1
        self.signal_type = 'voltage'
        self.bias_type = 'voltage'
        self.num_pts = 50
        self.meas_delay = 0.0
        self.enable_live_plots = False
        self.enable_live_vals = True

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

        # Begin ui setup by importing the ui file
        # print('Loading ui file from "{}"'.format(ui_path))
        self.ui = uic.loadUi(ui_path, self)

        # Define measurement setup tab
        self.tab_meas_setup = self.findChild(QWidget, 'tab_meas_setup')

        # Define controls for the overall measuring parameters
        self.gbox_meas_set_params = self.findChild(QGroupBox, 'gbox_meas_set_params')
        self.combo_function = self.findChild(QComboBox, 'combo_function')
        self.combo_meas_time = self.findChild(QComboBox, 'combo_meas_time')
        self.combo_range = self.findChild(QComboBox, 'combo_range')
        self.ln_data_averaging = self.findChild(QLineEdit, 'ln_data_averaging')
        self.ln_data_averaging.setText(str(self.data_averaging))
        self.combo_signal_type = self.findChild(QComboBox, 'combo_signal_type')
        self.combo_bias_type = self.findChild(QComboBox, 'combo_bias_type')
        self.ln_num_pts = self.findChild(QLineEdit, 'ln_num_pts')
        self.ln_num_pts.setText(str(self.num_pts))
        self.ln_step_delay = self.findChild(QLineEdit, 'ln_step_delay')
        self.ln_step_delay.setText(str(self.meas_delay))
        self.ln_notes = self.findChild(QLineEdit, 'ln_notes')
        self.ln_save_file = self.findChild(QLineEdit, 'ln_save_file')
        self.btn_save_file = self.findChild(QToolButton, 'btn_save_file')

        # Define controls for the per measurement settings
        self.gbox_meas_setup = self.findChild(QGroupBox, 'gbox_meas_setup')
        self.ln_num_meas = self.findChild(QLineEdit, 'ln_num_meas')
        self.ln_num_meas.setText(str(self.num_measurements))
        self.btn_copy_table = self.findChild(QPushButton, 'btn_copy_table')
        self.btn_paste_table = self.findChild(QPushButton, 'btn_paste_table')
        self.table_meas_setup = self.findChild(QTableWidget, 'table_meas_setup')
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Equilibration Delay [s]']
        self.meas_setup_vheaders = ['M1']

        # Define running measurement tab
        self.tab_run_meas = self.findChild(QWidget, 'tab_run_meas')

        # Create labels for the current measurement data
        self.lbl_curr_meas_start = self.findChild(QLabel, 'lbl_curr_meas_start')
        self.lbl_curr_meas_stop = self.findChild(QLabel, 'lbl_curr_meas_stop')
        self.lbl_curr_meas_osc = self.findChild(QLabel, 'lbl_curr_meas_osc')
        self.lbl_curr_meas_bias = self.findChild(QLabel, 'lbl_curr_meas_bias')
        self.progress_bar_meas = self.findChild(QProgressBar, 'progress_bar_meas')
        self.lbl_meas_progress = self.findChild(QLabel, 'lbl_meas_progress')
        self.lbl_meas_status = self.findChild(QLabel, 'lbl_meas_status')

        # Define value readouts
        self.gbox_val1 = self.findChild(QGroupBox, 'gbox_val1')
        self.lbl_val1 = self.findChild(QLabel, 'lbl_val1')
        self.gbox_val2 = self.findChild(QGroupBox, 'gbox_val2')
        self.lbl_val2 = self.findChild(QLabel, 'lbl_val2')
        self.gbox_curr_freq = self.findChild(QGroupBox, 'gbox_curr_freq')
        self.lbl_curr_freq = self.findChild(QLabel, 'lbl_curr_freq')

        self.live_plot = self.findChild(LivePlotWidget, 'live_plot')

        self.init_measure_worker()

        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()
        self.live_readout_timer = QTimer()
        self.btn_run_start_stop = self.findChild(QPushButton, 'btn_run_start_stop')
        self.btn_setup_start_stop = self.findChild(QPushButton, 'btn_setup_start_stop')

        # Set up for allowing copy paste in the measurement table
        self.clipboard = QApplication.clipboard()
        self.copy_sc = QShortcut(QKeySequence('Ctrl+C'), self.table_meas_setup, self.copy_table, self.copy_table)
        self.paste_sc = QShortcut(QKeySequence('Ctrl+V'), self.table_meas_setup, self.paste_table, self.paste_table)

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()
        # print('Capacitance-Frequency initialization complete')

    def init_connections(self):
        # Control edit connections
        self.combo_function.currentTextChanged.connect(self.change_function)
        self.combo_meas_time.currentTextChanged.connect(self.change_meas_aperture)
        self.ln_data_averaging.editingFinished.connect(self.change_meas_aperture)
        self.ln_num_pts.editingFinished.connect(self.change_num_pts)
        self.ln_step_delay.editingFinished.connect(self.change_step_delay)
        self.combo_range.currentTextChanged.connect(self.change_impedance_range)
        self.combo_signal_type.currentTextChanged.connect(self.change_signal_type)
        self.combo_bias_type.currentTextChanged.connect(self.change_bias_type)
        self.ln_save_file.editingFinished.connect(self.set_save_file_path_by_line)
        self.btn_save_file.clicked.connect(self.set_save_file_path_by_dialog)
        self.ln_num_meas.editingFinished.connect(self.change_num_measurements)
        self.btn_copy_table.clicked.connect(self.copy_table)
        self.btn_paste_table.clicked.connect(self.paste_table)
        self.btn_run_start_stop.clicked.connect(self.on_start_stop_clicked)
        self.btn_setup_start_stop.clicked.connect(self.on_start_stop_clicked)

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
        self.measuring_worker = CapFreqMeasureWorkerObject(self)
        self.measuring_worker.moveToThread(self.measuring_thread)
        # self.lcr.moveToThread(self.measuring_thread)

    def init_control_setup(self):
        self.init_setup_table()

        # Set up comboboxes
        self.combo_range.addItems(Const.VALID_IMP_RANGES)
        self.combo_function.addItems(list(Const.FUNC_DICT.keys()))
        self.combo_meas_time.addItems(list(Const.MEASURE_TIME_DICT.keys()))
        self.combo_signal_type.addItems(['Voltage', 'Current'])
        self.combo_bias_type.addItems(['Voltage', 'Current'])

        # Set up timers
        self.live_readout_timer.start(500)

    def init_setup_table(self):
        # Set up initial table headers and size
        self.table_meas_setup.setRowCount(1)
        self.table_meas_setup.setColumnCount(5)
        self.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.table_meas_setup.setVerticalHeaderLabels(self.meas_setup_vheaders)
        self.table_meas_setup.setWordWrap(True)
        self.table_meas_setup.resizeColumnsToContents()
        self.add_table_items()
        self.table_meas_setup.item(0, 0).setText('20')
        self.table_meas_setup.item(0, 1).setText('2000000')
        self.table_meas_setup.item(0, 2).setText('0.05')
        self.table_meas_setup.item(0, 3).setText('0')
        self.table_meas_setup.item(0, 4).setText('0')

    def get_new_data(self):
        # Helper function to get new data on timer timeout. Was failing when called directly, could be something about
        #  having a return value?
        if self.enable_live_vals:
            self.lcr.get_data()

    def change_function(self):
        self.lcr_function = self.combo_function.currentText()
        self.update_val_labels()

    def change_meas_aperture(self):
        self.measuring_time = self.combo_meas_time.currentText()
        try:
            self.data_averaging = int(self.ln_data_averaging.text())
        except ValueError:
            self.data_averaging = 1
            self.ln_data_averaging.setText(str(self.data_averaging))

    def change_num_pts(self):
        try:
            self.num_pts = int(self.ln_num_pts.text())
        except ValueError:
            self.num_pts = 50
            self.ln_num_pts.setText(str(self.num_pts))

    def change_step_delay(self):
        try:
            self.meas_delay = float(self.ln_step_delay.text())
        except ValueError:
            self.meas_delay = 0.0
            self.ln_step_delay.setText(str(self.meas_delay))

    def change_impedance_range(self):
        self.range = self.combo_range.currentText()

    def change_signal_type(self):
        self.signal_type = self.combo_signal_type.currentText()

    def change_bias_type(self):
        self.bias_type = self.combo_bias_type.currentText()

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

        self.ln_save_file.setText(self.save_file_path)

    def set_save_file_path_by_line(self):
        if self.ln_save_file.text() != '':
            self.save_file_path = self.ln_save_file.text()

    def change_num_measurements(self):
        num = self.num_measurements
        try:
            self.num_measurements = int(self.ln_num_meas.text())
        except ValueError:
            self.num_measurements = num

        self.table_meas_setup.setRowCount(self.num_measurements)
        self.update_table_vheaders()
        self.add_table_items()

    def update_live_readout(self, data: list):
        self.lbl_curr_freq.setText(str(Static.si_prefix(data[0], 'Hz', 4)))
        self.lbl_val1.setText(str(Static.to_sigfigs(data[1], 6)))
        self.lbl_val2.setText(str(Static.to_sigfigs(data[2], 6)))

    def update_table_hheaders(self):
        self.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)

    def update_table_vheaders(self):
        self.meas_setup_vheaders = ['M{}'.format(x) for x in range(1, self.num_measurements + 1)]
        self.table_meas_setup.setVerticalHeaderLabels(self.meas_setup_vheaders)

    def add_table_items(self):
        for irow in range(0, self.table_meas_setup.rowCount()):
            for icol in range(0, self.table_meas_setup.columnCount()):
                widget = self.table_meas_setup.item(irow, icol)
                # If the cell doesn't already have a QTableWidgetItem
                if widget is None:
                    # Create a new QTableWidgetItem in the cell
                    new_widget = QTableWidgetItem()
                    if irow > 0:
                        # Get the value of the cell above
                        value = self.table_meas_setup.item(irow - 1, icol).text()
                        new_widget.setText(value)
                    # Put the new widget in the table
                    self.table_meas_setup.setItem(irow, icol, new_widget)

    def copy_table(self):
        tmprow = ''
        copystr = ''

        for irow in range(0, self.table_meas_setup.rowCount()):
            for icol in range(0, self.table_meas_setup.columnCount()):
                tmprow = tmprow + self.table_meas_setup.item(irow, icol).text() + '\t'

            copystr = copystr + tmprow.rstrip('\t') + '\n'
            tmprow = ''

        self.clipboard.setText(copystr)

    def paste_table(self):
        rows = self.clipboard.text().split('\n')[:-1]

        self.num_measurements = len(rows)
        self.ln_num_meas.setText(str(len(rows)))
        self.change_num_measurements()

        for (irow, row_val) in enumerate(rows):
            tmpcols = row_val.split('\t')
            for (icol, col_val) in enumerate(tmpcols):
                self.table_meas_setup.item(irow, icol).setText(str(col_val))

    def generate_header(self, index, row):
        header_vars = self.get_header_vars(index, row)

        header = CAP_FREQ_HEADER.format(meas_type=self.lcr_function,
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
                                        notes='Notes:\t{}'.format(header_vars['notes']))

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
        if self.combo_signal_type.currentText() == 'Voltage':
            header_vars['osc_type'] = 'V'
        elif self.combo_signal_type.currentText() == 'Current':
            header_vars['osc_type'] = 'A'
        else:
            header_vars['osc_type'] = 'UNKNOWN'

        header_vars['bias'] = row[self.meas_setup_hheaders[3]]
        if self.combo_bias_type.currentText() == 'Voltage':
            header_vars['bias_type'] = 'V'
        elif self.combo_bias_type.currentText() == 'Current':
            header_vars['bias_type'] = 'A'
        else:
            header_vars['bias_type'] = 'UNKNOWN'

        header_vars['notes'] = self.ln_notes.text()

        return header_vars

    def generate_test_matrix(self):
        self.tests_df = pd.DataFrame(data=None, index=self.meas_setup_vheaders, columns=self.meas_setup_hheaders)

        for irow in range(0, self.table_meas_setup.rowCount()):
            for icol in range(0, self.table_meas_setup.columnCount()):
                self.tests_df.iloc[irow, icol] = self.table_meas_setup.item(irow, icol).text()

    def enable_controls(self, enable: bool):
        self.gbox_meas_setup.setEnabled(enable)
        self.gbox_meas_set_params.setEnabled(enable)

    def setup_lcr(self):
        self.lcr.function(self.lcr_function)
        self.lcr.impedance_range(self.range)
        self.lcr.measurement_aperture(self.measuring_time, self.data_averaging)
        self.lcr.signal_level(self.signal_type, self.table_meas_setup.item(0, 2).text())
        self.lcr.dc_bias_level(self.bias_type, self.table_meas_setup.item(0, 3).text())

    def on_start_stop_clicked(self):
        # Get the sender
        btn = self.sender()
        # If the sender is checked (trying to start the measurement)
        if btn.isChecked():
            # Set both buttons to checked
            self.btn_setup_start_stop.setChecked(True)
            self.btn_run_start_stop.setChecked(True)
            # Pause the update timer
            self.enable_live_vals = False
            # Set the text on both buttons
            self.btn_setup_start_stop.setText('Stop Measurements')
            self.btn_run_start_stop.setText('Stop Measurements')
            # Start the measurement
            self.start_measurement()
        # If the sender is not checked (User has cancelled measurement)po0909o0poi9o
        elif not btn.isChecked():
            # Set both buttons to unchecked
            self.btn_setup_start_stop.setChecked(False)
            self.btn_run_start_stop.setChecked(False)
            # Enable the update timer
            self.enable_live_vals = True
            # Set the text on both buttons
            self.btn_setup_start_stop.setText('Run Measurement Set')
            self.btn_run_start_stop.setText('Run Measurement Set')
            # Start the measurement
            self.halt_measurement()

    def move_instr_to_worker_thread(self):
        self.lcr.moveToThread(self.measuring_thread)

    def halt_measurement(self):
        self.stop_measurement_worker.emit()
        self.enable_live_plots = False
        self.enable_live_vals = True
        self.enable_controls(True)

    def start_measurement(self):
        self.set_save_file_path_by_line()
        self.check_file_path()

        self.setCurrentWidget(self.tab_run_meas)
        # Set up the progress bar for this measurement
        self.progress_bar_meas.setMinimum(0)
        self.progress_bar_meas.setMaximum(self.num_measurements * self.num_pts)
        self.progress_bar_meas.reset()
        # Keep the user from changing values in the controls
        self.enable_controls(False)
        # Set live vals to update to last read value only
        self.enable_live_vals = False
        # Enable live plotting of values, clear previous data
        self.live_plot.clear_data()
        self.enable_live_plots = True

        self.move_instr_to_worker_thread()
        # Emit signal to start the worker measuring
        self.measuring_thread.start()

    def dep_cancelled_by_user(self):
        cancel = QMessageBox.information(self, 'Measurement canceled',
                                         'Measurement cancelled by user.',
                                         QMessageBox.Ok, QMessageBox.Ok)
        if cancel == QMessageBox.Ok:
            self.btn_setup_start_stop.setChecked(False)
            self.btn_run_start_stop.setChecked(False)
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
        self.btn_setup_start_stop.setChecked(False)
        self.btn_run_start_stop.setChecked(False)
        # Set the text on both buttons
        self.btn_setup_start_stop.setText('Start Measurements')
        self.btn_run_start_stop.setText('Start Measurements')

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
                self.live_plot.add_data([zreal, -1 * zimag])
            else:
                self.live_plot.add_data([data[0], data[1], data[2]])

    def update_val_labels(self):
        # Get the two parameters that are being measured/output
        val_params = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.lcr_function]]

        # Handle special cases for the live plot
        if self.lcr_function == 'Z-Thd':
            self.live_plot.canvas.set_dual_y(False, ["Z' (Ohm)", "-Z'' (Ohm)"])
        else:
            self.live_plot.canvas.set_dual_y(True, ['Frequency [Hz]', val_params[0], val_params[1]])

        # Set the live value readout names regardless
        self.gbox_val1.setTitle(val_params[0])
        self.gbox_val2.setTitle(val_params[1])

    def update_measurement_progress(self, indices: list):
        # NOTE: indices[0] will be the measurement number (one indexed), and
        # indices[1] will be the step number (Zero indexed)
        self.progress_bar_meas.setValue(((indices[0] - 1) * self.num_pts) + (indices[1] + 1))
        self.lbl_meas_progress.setText('Measurement {}/{},\nStep {}/{}'.format(indices[0], self.num_measurements,
                                                                               indices[1] + 1, self.num_pts))

    def update_meas_status(self, update_str: str):
        self.lbl_meas_status.setText(update_str)


class CapFreqMeasureWorkerObject(QObject):
    measurement_finished = pyqtSignal()
    freq_step_finished = pyqtSignal(list)
    meas_status_update = pyqtSignal(str)

    def __init__(self, parent: CapFreqWidget):
        super().__init__()
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

    def stop_early(self):
        self.stop = True

    def set_current_meas_labels(self):
        self.parent.lbl_curr_meas_start.setText(str(self.step_start))
        self.parent.lbl_curr_meas_stop.setText(str(self.step_stop))
        self.parent.lbl_curr_meas_osc.setText(str(self.step_osc))
        self.parent.lbl_curr_meas_bias.setText(str(self.step_bias))

    def set_test_params(self, row):
        # Set up current test specific values
        self.step_start = row[self.parent.meas_setup_hheaders[0]]
        self.step_stop = row[self.parent.meas_setup_hheaders[1]]
        self.step_osc = row[self.parent.meas_setup_hheaders[2]]
        self.step_bias = row[self.parent.meas_setup_hheaders[3]]
        self.step_delay = float(row[self.parent.meas_setup_hheaders[4]])

    def get_out_columns(self):
        columns = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.parent.combo_function.currentText()]]
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
        pass

    def condition_equilibration_delay(self):
        count = 0
        while count < self.step_delay:
            time_left = str(timedelta(seconds=self.step_delay - count))
            self.meas_status_update.emit('Waiting for sample equilibration. Time Remaining: '
                                         '{}s'.format(time_left))
            sleep(1)
            count += 1

    def return_instr_to_main_thread(self):
        self.lcr.moveToThread(QApplication.instance().thread())

    def measurement_cleanup(self):
        self.meas_status_update.emit('Measurement finished.')

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
            self.parent.lcr.signal_level(self.parent.combo_signal_type.currentText(), self.step_osc)
            self.parent.lcr.dc_bias_level(self.parent.combo_bias_type.currentText(), self.step_bias)

            # Generate frequency points for measurement
            freq_steps = Static.generate_log_steps(int(self.step_start),
                                                   int(self.step_stop),
                                                   int(self.parent.num_pts))

            # Delay to allow sample to equilibrate at measurement parameters
            self.condition_equilibration_delay()

            # Start a new data line in each plot
            self.parent.live_plot.canvas.start_new_line()

            self.meas_status_update.emit('Measurement in progress...')

            for step_idx in range(0, len(freq_steps)):
                # Set the lcr to the correct frequency
                self.parent.lcr.signal_frequency(freq_steps[step_idx])

                # Wait for measurement to stabilize (50ms to allow signal to stabilize + user set delay)
                sleep(self.parent.meas_delay + 0.05)

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
#if standalone == 'capfreq':
    lcr = AgilentE4980A(parent=None, gpib_addr='GPIB0::17::INSTR')
    app = QApplication(sys.argv)
    main_window = CapFreqWidget(lcr=lcr)
    main_window.show()
    sys.exit(app.exec_())
