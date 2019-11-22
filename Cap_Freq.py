from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QComboBox, QLineEdit, QLabel, QFormLayout, QVBoxLayout,
                             QGroupBox, QTableWidget, QTableWidgetItem, QTabWidget, QHBoxLayout, QMessageBox,
                             QToolButton, QApplication, QFileDialog, QFrame, QStyleFactory, QProgressBar, QPushButton)
from PyQt5.QtCore import QTimer, QThread, Qt, QSize, pyqtSignal, QObject
import sys
import os
from io import StringIO
from time import sleep
import pandas as pd
from datetime import datetime
from Live_Data_Plotter import LivePlotWidget
#from Agilent_E4980A import AgilentE4980A
# Can be used to emulate the LCR without connection data will be garbage (random numbers)
from fake_E4980 import AgilentE4980A
import Agilent_E4980A_Constants as Const
from File_Print_Headers import *
import Static_Functions as Static


class CapFreqWidget (QTabWidget):
    # This signal needs to be defined before the __init__ in order to allow it to work
    stop_measurement_worker = pyqtSignal()

    def __init__(self, lcr: AgilentE4980A):
        super().__init__()

        # Define class variables and objects
        self.lcr = lcr
        self.lcr_function = 'self.lcr.get_current_function()'  # Dummy value which is set after connection
        self.measuring_time = 'long'
        self.range = 'auto'
        self.data_averaging = 1
        self.signal_type = 'voltage'
        self.bias_type = 'voltage'
        self.num_pts = 50
        self.step_delay = 0.0
        self.enable_live_plots = False

        self.num_measurements = 1
        self.tests_df = pd.DataFrame()
        self.data_dict = {}
        self.header_dict = {}
        self.save_file_path = os.path.join(os.getenv('USERPROFILE'), 'Desktop')

        # Tiny bit of initial instrument setup
        self.lcr.dc_bias_state('on')
        self.return_to_defaults()

        # Begin ui setup by importing the ui file
        self.ui = uic.loadUi('./src/ui/cap_freq_tabs.ui', self)

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
        self.ln_step_delay.setText(str(self.step_delay))
        self.ln_notes = self.findChild(QLineEdit, 'ln_notes')
        self.ln_save_file = self.findChild(QLineEdit, 'ln_save_file')
        self.btn_save_file = self.findChild(QToolButton, 'btn_save_file')

        # Define controls for the per measurement settings
        self.gbox_meas_setup = self.findChild(QGroupBox, 'gbox_meas_setup')
        self.ln_num_meas = self.findChild(QLineEdit, 'ln_num_meas')
        self.ln_num_meas.setText(str(self.num_measurements))
        self.table_meas_setup = self.findChild(QTableWidget, 'table_meas_setup')
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Measurement Delay [s]']
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

        # Define value readouts
        self.gbox_val1 = self.findChild(QGroupBox, 'gbox_val1')
        self.lbl_val1 = self.findChild(QLabel, 'lbl_val1')
        self.gbox_val2 = self.findChild(QGroupBox, 'gbox_val2')
        self.lbl_val2 = self.findChild(QLabel, 'lbl_val2')
        # Fixme: set this up to be updated with each new measurement step
        self.gbox_curr_freq = self.findChild(QGroupBox, 'gbox_curr_freg')
        self.lbl_curr_freq = self.findChild(QLabel, 'lbl_curr_freq')

        self.live_plot = self.findChild(LivePlotWidget, 'live_plot')

        # Create a thread to use for measuring data
        self.measuring_thread = QThread()
        self.measuring_worker = MeasureWorkerObj(self)
        self.measuring_worker.moveToThread(self.measuring_thread)
        self.lcr.moveToThread(self.measuring_thread)

        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()
        self.live_readout_timer = QTimer()
        self.btn_run_start_stop = self.findChild(QPushButton, 'btn_run_start_stop')
        self.btn_setup_start_stop = self.findChild(QPushButton, 'btn_setup_start_stop')

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()

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

    def init_control_setup(self):
        # Set up initial table headers and size
        self.table_meas_setup.setRowCount(1)
        self.table_meas_setup.setColumnCount(5)
        self.table_meas_setup.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.table_meas_setup.setVerticalHeaderLabels(self.meas_setup_vheaders)
        self.table_meas_setup.setWordWrap(True)
        self.table_meas_setup.resizeColumnsToContents()
        self.add_table_items()
        self.table_meas_setup.item(0, 0).setText('20')
        self.table_meas_setup.item(0, 1).setText('1000000')
        self.table_meas_setup.item(0, 2).setText('0.05')
        self.table_meas_setup.item(0, 3).setText('0')
        self.table_meas_setup.item(0, 4).setText('0')

        # Set up comboboxes
        self.combo_range.addItems(Const.VALID_IMP_RANGES)
        self.combo_function.addItems(list(Const.FUNC_DICT.keys()))
        self.combo_meas_time.addItems(list(Const.MEASURE_TIME_DICT.keys()))
        self.combo_signal_type.addItems(['Voltage', 'Current'])
        self.combo_bias_type.addItems(['Voltage', 'Current'])

        # Set up timers
        self.live_readout_timer.start(500)

    def get_new_data(self):
        # Helper function to get new data on timer timeout. Was failing when called directly, could be something about
        #  having a return value?
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
            self.step_delay = float(self.ln_step_delay.text())
        except ValueError:
            self.step_delay = 0.0
            self.ln_step_delay.setText(str(self.step_delay))

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

    def generate_header(self, index, row):
        # Gather format strings for header
        meas_number = index
        now = datetime.now()
        date_now = str(now).split(' ')[0]
        time_now = str(now.strftime('%H:%M:%S'))

        start = row[self.meas_setup_hheaders[0]]
        stop = row[self.meas_setup_hheaders[1]]

        osc = row[self.meas_setup_hheaders[2]]
        if self.combo_signal_type.currentText() == 'Voltage':
            osc_type = 'V'
        elif self.combo_signal_type.currentText() == 'Current':
            osc_type = 'A'
        else:
            osc_type = 'UNKNOWN'

        bias = row[self.meas_setup_hheaders[3]]
        if self.combo_bias_type.currentText() == 'Voltage':
            bias_type = 'V'
        elif self.combo_bias_type.currentText() == 'Current':
            bias_type = 'A'
        else:
            bias_type = 'UNKNOWN'

        notes = self.ln_notes.text()

        header = CAP_FREQ_HEADER.format(self.lcr_function,
                                        date_now,
                                        time_now,
                                        meas_number,
                                        start,
                                        stop,
                                        osc_type, osc,
                                        bias_type, bias,
                                        self.step_delay,
                                        'Notes:\t{}'.format(notes))

        return header

    def generate_test_matrix(self):
        self.tests_df = pd.DataFrame(data=None, index=self.meas_setup_vheaders, columns=self.meas_setup_hheaders)

        for irow in range(0, self.table_meas_setup.rowCount()):
            for icol in range(0, self.table_meas_setup.columnCount()):
                self.tests_df.iloc[irow, icol] = self.table_meas_setup.item(irow, icol).text()

    def enable_controls(self, enable: bool):
        self.gbox_meas_setup.setEnabled(enable)
        self.gbox_meas_set_params.setEnabled(enable)

    def enable_live_val_timer(self, enable: bool):
        try:
            if enable:
                self.live_readout_timer.timeout.connect(self.get_new_data)
            elif not enable:
                self.live_readout_timer.timeout.disconnect(self.get_new_data)
        except TypeError:
            print('Unable to disconnect or reconnect live value timer correctly')

    def setup_lcr(self):
        self.lcr.function(self.lcr_function)
        self.lcr.impedance_range(self.range)
        self.lcr.measurement_aperture(self.measuring_time, self.data_averaging)
        self.lcr.signal_level(self.signal_type, self.table_meas_setup.item(0, 2).text())
        self.lcr.dc_bias_level(self.bias_type, self.table_meas_setup.item(0, 3).text())

    # Fixme: I think this will mostly still work, but I need to set it up for the checking and unchecking rather than
    #  manual icon changes and connect/disconnect.

    def on_start_stop_clicked(self):
        # Get the sender
        btn = self.sender()
        print(btn)
        # If the sender is not checked (trying to start the measurement)
        if btn.isChecked():
            # Set both buttons to checked
            self.btn_setup_start_stop.setChecked(True)
            self.btn_run_start_stop.setChecked(True)
            # Pause the update timer
            self.enable_live_val_timer(False)
            # Set the text on both buttons
            self.btn_setup_start_stop.setText('Stop Measurements')
            self.btn_run_start_stop.setText('Stop Measurements')
            # Start the measurement
            self.start_measurement()
        # If the sender is checked (User has cancelled measurement)po0909o0poi9o
        elif not btn.isChecked():
            # Set both buttons to unchecked
            self.btn_setup_start_stop.setChecked(False)
            self.btn_run_start_stop.setChecked(False)
            # Enable the update timer
            self.enable_live_val_timer(True)
            # Set the text on both buttons
            self.btn_setup_start_stop.setText('Run Measurement Set')
            self.btn_run_start_stop.setText('Run Measurement Set')
            # Start the measurement
            self.halt_measurement()

    def halt_measurement(self):
        self.stop_measurement_worker.emit()

    def start_measurement(self):
        self.set_save_file_path_by_line()
        print(self.save_file_path)
        if os.path.isfile(self.save_file_path):
            overwrite = QMessageBox.warning(self, 'File already exists',
                                            'This data file already exists. Would you like to overwrite?',
                                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                            QMessageBox.No)
            if overwrite == QMessageBox.No:
                self.set_save_file_path_by_dialog()
                self.start_measurement()
            elif overwrite == QMessageBox.Cancel:
                cancel = QMessageBox.information(self, 'Measurement canceled',
                                                 'Measurement cancelled by user.',
                                                 QMessageBox.Ok, QMessageBox.Ok)
                if cancel == QMessageBox.Ok:
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
                cancel = QMessageBox.information(self, 'Measurement canceled',
                                                 'Measurement cancelled by user.',
                                                 QMessageBox.Ok, QMessageBox.Ok)
                if cancel == QMessageBox.Ok:
                    return
        # Fixme: maybe add more file save path checking i.e. blank or default location.

        self.setCurrentWidget(self.tab_run_meas)
        # Set up the progress bar for this measurement
        self.progress_bar_meas.setMinimum(0)
        self.progress_bar_meas.setMaximum(self.num_measurements * self.num_pts)
        self.progress_bar_meas.reset()
        # Keep the user from changing values in the controls
        self.enable_controls(False)
        # Set live vals to update to last read value only
        self.enable_live_val_timer(False)
        # Enable live plotting of values, clear previous data
        self.live_plot.clear_data()
        self.enable_live_plots = True

        # Emit signal to start the worker measuring
        self.measuring_thread.start()

    # When the worker says it is done, save data and reset widget state to interactive
    def end_measurement(self):
        self.save_data()

        # Enable the user to change controls
        self.enable_controls(True)
        # Set live vals to update periodically
        self.enable_live_val_timer(True)
        # Disable live plotting of values
        self.enable_live_plots =  False
        self.return_to_defaults()

        print('Measurement finished')
        # Change start/stop button back to start
        # Set both buttons to unchecked
        self.btn_setup_start_stop.setChecked(False)
        self.btn_run_start_stop.setChecked(False)
        # Set the text on both buttons
        self.btn_setup_start_stop.setText('Start Measurements')
        self.btn_run_start_stop.setText('Start Measurements')

    def return_to_defaults(self):
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
            self.live_plot.add_data([data[0], data[1], data[2]])

    def update_val_labels(self):
        val_params = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.lcr_function]]
        self.live_plot.update_plot_labels(['Frequency [Hz]', val_params[0], val_params[1]])
        self.gbox_val1.setTitle(val_params[0])
        self.gbox_val2.setTitle(val_params[1])

    def update_measurement_progress(self, indices: list):
        # NOTE: indices[0] will be the measurement number (one indexed), and
        # indices[1] will be the step number (Zero indexed)
        self.progress_bar_meas.setValue(((indices[0] - 1) * self.num_pts) + (indices[1] + 1))
        self.lbl_meas_progress.setText('Measurement {}/{},\nStep {}/{}'.format(indices[0], self.num_measurements,
                                                                               indices[1] + 1, self.num_pts))


class MeasureWorkerObj (QObject):
    measurement_finished = pyqtSignal()
    freq_step_finished = pyqtSignal(list)

    def __init__(self, parent: CapFreqWidget):
        super().__init__()
        self.parent = parent
        self.stop = False
        self.parent.stop_measurement_worker.connect(self.stop_early)

    def stop_early(self):
        self.stop = True

    def set_current_meas_labels(self, start, stop, osc, bias):
        self.parent.lbl_curr_meas_start.setText(str(start))
        self.parent.lbl_curr_meas_stop.setText(str(stop))
        self.parent.lbl_curr_meas_osc.setText(str(osc))
        self.parent.lbl_curr_meas_bias.setText(str(bias))

    def measure(self):
        # Write configured parameters to lcr
        self.parent.setup_lcr()

        # Generate the matrix of tests to run
        self.parent.generate_test_matrix()

        # Set up the data column headers
        columns = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.parent.combo_function.currentText()]]
        if columns[0] != 'Frequency [Hz]':
            columns.insert(0, 'Frequency [Hz]')
        # For each measurement in the test matrix
        for index, row in self.parent.tests_df.iterrows():
            # Create an empty data frame to hold results, Column Headers determined by measurement type
            data_df = pd.DataFrame(data=None,
                                   columns=columns)

            # Pull in test specific values
            start = row[self.parent.meas_setup_hheaders[0]]
            stop = row[self.parent.meas_setup_hheaders[1]]
            osc = row[self.parent.meas_setup_hheaders[2]]
            bias = row[self.parent.meas_setup_hheaders[3]]
            delay = int(row[self.parent.meas_setup_hheaders[4]])
            # ToDo: Should delay be added to the current measurement labels?
            self.set_current_meas_labels(start, stop, osc, bias)

            # ToDo: Should this set to defualt during this wait? Seems like yes to avoid over exposure to
            #  bias/signal. Also user can set settling time elsewhere that would allow sample to be exposed
            #  to measuring conditions longer.
            self.parent.return_to_defaults()
            count = 0
            while count < delay:
                sleep(1)
                if (delay - count) > 10 and not (count % 10):
                    print('Sleeping until measurement time. Time Remaining: {}s'.format((delay-count)))
                elif (delay-count) <= 10:
                    print('Sleeping until measurement time. Time Remaining: {}s'.format((delay - count)))
                count += 1
                
            print('Beginning measurement...')
            # Set lcr accordingly
            self.parent.lcr.signal_level(self.parent.combo_signal_type.currentText(), osc)
            self.parent.lcr.dc_bias_level(self.parent.combo_bias_type.currentText(), bias)

            freq_steps = Static.generate_log_steps(int(start), int(stop), int(self.parent.num_pts))

            # Start a new data line in each plot
            self.parent.live_plot.live_plot.start_new_line()

            for step_idx in range(0, len(freq_steps)):
                # Set the lcr to the correct frequency
                self.parent.lcr.signal_frequency(freq_steps[step_idx])

                # Wait for measurement to stabilize (50ms to allow signal to stabilize + user set delay)
                sleep(self.parent.step_delay + 0.05)

                # Trigger the measurement to start
                self.parent.lcr.trigger_init()

                # Read the measurement result
                data = self.parent.lcr.get_data()
                data = pd.Series(data, index=data_df.columns)

                # Store the data to the data_df
                data_df = data_df.append(data, ignore_index=True)
                self.freq_step_finished.emit([int(index.split('M')[-1]), step_idx])
                QApplication.processEvents()  # Checks if measurement has been stopped.
                if self.stop:
                    break
            if self.stop:
                break

            # Store the measurement data in a field of the tests_df
            self.parent.header_dict[index] = self.parent.generate_header(index, row)
            self.parent.data_dict[index] = data_df

        self.stop = False
        self.measurement_finished.emit()


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create('Fusion'))
gui = CapFreqWidget(AgilentE4980A())
gui.show()

sys.exit(app.exec_())
