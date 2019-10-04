from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QComboBox, QLineEdit, QLabel, QFormLayout, QVBoxLayout,
                             QGroupBox, QTableWidget, QTableWidgetItem, QTabWidget, QHBoxLayout, QMessageBox,
                             QToolButton, QApplication, QFileDialog, QFrame, QStyleFactory, QProgressBar)
from PyQt5.QtCore import QTimer, QThread, Qt, QSize, pyqtSignal, QObject
import sys
from pathlib import Path
import os
from io import StringIO
from time import sleep
import pandas as pd
from datetime import datetime
from Live_Data_Plotter import LivePlotWidget
from Agilent_E4980A import AgilentE4980A
# from fake_E4980 import AgilentE4980A
import Agilent_E4980A_Constants as Const
import FormatLib
from File_Print_Headers import *
import Static_Functions as Static


class CapFreqWidget (QTabWidget):
    # This signal needs to be defined before the __init__ in order to allow it to work
    start_measurement_worker = pyqtSignal()
    stop_measurement_worker = pyqtSignal()

    def __init__(self, lcr: AgilentE4980A):
        super().__init__()

        # Define class variables and objects
        self.lcr = lcr
        self.lcr_function = 'self.lcr.get_current_function()'
        self.measuring_time = 'long'
        self.range = 'auto'
        self.measuring_avg = 1
        self.signal_type = 'voltage'
        self.bias_type = 'voltage'
        self.num_data_pts = 50
        self.step_delay = 0.0

        self.num_measurements = 1
        self.tests_df = pd.DataFrame()
        self.data_dict = {}
        self.header_dict = {}
        self.save_file_path = os.path.join(os.getenv('USERPROFILE'), 'Desktop')

        # Tiny bit of initial instrument setup
        self.lcr.dc_bias_state('on')
        self.return_to_defaults()

        # Create a thread to use for measuring data
        self.measuring_thread = QThread()
        self.measuring_worker = MeasureWorkerObj(self, self.lcr)
        self.measuring_worker.moveToThread(self.measuring_thread)
        self.lcr.moveToThread(self.measuring_thread)

        # Define measurement setup tab
        self.meas_setup_tab = QWidget()

        # Define controls for the overall measuring parameters
        self.measuring_param_box = QGroupBox('Measuring Parameters:')
        self.function_combo = QComboBox()
        self.measuring_time_combo = QComboBox()
        self.range_combo = QComboBox()
        self.measuring_avg_ln = QLineEdit(str(self.measuring_avg))
        self.signal_type_combo = QComboBox()
        self.bias_type_combo = QComboBox()
        self.num_data_pts_ln = QLineEdit(str(self.num_data_pts))
        self.step_delay_ln = QLineEdit(str(self.step_delay))
        self.notes = QLineEdit()
        self.save_file_ln = QLineEdit()
        self.save_file_btn = QToolButton()
        self.meas_progress_bar = QProgressBar()
        self.meas_progress_lbl = QLabel()

        # Define controls for the per measurement settings
        self.meas_setup_box = QGroupBox('Measurement(s) Setup:')
        self.num_measurements_ln = QLineEdit(str(self.num_measurements))
        self.meas_setup_table = QTableWidget()
        self.meas_setup_hheaders = ['Frequency Start [Hz]',
                                    'Frequency Stop [Hz]',
                                    'Oscillator [V]',
                                    'DC Bias [V]',
                                    'Measurement Delay [s]']
        self.meas_setup_vheaders = ['M1']

        # Define running measurement tab
        self.meas_run_tab = QWidget()

        # Create labels for the current measurement data
        self.curr_meas_start = QLabel()
        self.curr_meas_stop = QLabel()
        self.curr_meas_osc = QLabel()
        self.curr_meas_bias = QLabel()

        # Define stuff for live plotting and value readout
        self.val1_frame = QGroupBox()
        self.val1_lbl = QLabel()
        self.val1_live_plot = LivePlotWidget(['Frequency [Hz]', 'val_params[0]'],
                                             lead=False,
                                             head=True,
                                             draw_interval=350)
        self.val2_frame = QGroupBox()
        self.val2_lbl = QLabel()
        self.val2_live_plot = LivePlotWidget(['Frequency [Hz]', 'val_params[1]'],
                                             lead=False,
                                             head=True,
                                             draw_interval=350)
        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()
        self.live_readout_timer = QTimer()
        self.save_icon = QIcon()
        self.run_icon = QIcon()
        self.stop_icon = QIcon()
        self.run_start_meas_btn = QToolButton()
        self.setup_start_meas_btn = QToolButton()

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()
        self.init_layout()

    def init_connections(self):
        # Control edit connections
        self.function_combo.currentTextChanged.connect(self.change_function)
        self.measuring_time_combo.currentTextChanged.connect(self.change_meas_aperture)
        self.measuring_avg_ln.editingFinished.connect(self.change_meas_aperture)
        self.num_data_pts_ln.editingFinished.connect(self.change_num_pts)
        self.step_delay_ln.editingFinished.connect(self.change_step_delay)
        self.range_combo.currentTextChanged.connect(self.change_impedance_range)
        self.signal_type_combo.currentTextChanged.connect(self.change_signal_type)
        self.bias_type_combo.currentTextChanged.connect(self.change_bias_type)
        self.save_file_ln.editingFinished.connect(self.set_save_file_path_by_text)
        self.save_file_btn.clicked.connect(self.set_save_file_path_by_dialog)
        # self.save_file_btn.clicked.connect(self.print_size)   # DEBUG FOR SETTING SIZES
        self.num_measurements_ln.editingFinished.connect(self.change_num_measurements)
        self.run_start_meas_btn.clicked.connect(self.start_measurement)
        self.setup_start_meas_btn.clicked.connect(self.start_measurement)
        # self.start_meas_btn.clicked.connect(self.change_start_button)

        # Timers
        self.live_readout_timer.timeout.connect(self.lcr.get_data)
        self.lcr.new_data.connect(self.update_live_readout)
        # Gets data and emits a signal to update live value readouts
        self.lcr.get_data()

        # Cross thread communication
        self.measuring_worker.measurement_finished.connect(self.measuring_thread.quit)
        self.stop_measurement_worker.connect(self.measuring_worker.stop_early)
        self.measuring_worker.freq_step_finished.connect(self.update_measurement_progress)
        self.measuring_thread.finished.connect(self.end_measurement)
        self.measuring_thread.started.connect(self.measuring_worker.measure)

    def init_control_setup(self):
        # Set up initial table headers and size
        self.meas_setup_table.setRowCount(1)
        self.meas_setup_table.setColumnCount(5)
        self.meas_setup_table.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.meas_setup_table.setVerticalHeaderLabels(self.meas_setup_vheaders)
        self.meas_setup_table.setWordWrap(True)
        self.meas_setup_table.resizeColumnsToContents()
        self.add_table_items()
        self.meas_setup_table.item(0, 0).setText('20')
        self.meas_setup_table.item(0, 1).setText('1000000')
        self.meas_setup_table.item(0, 2).setText('0.05')
        self.meas_setup_table.item(0, 3).setText('0')
        self.meas_setup_table.item(0, 4).setText('0')

        # Set up comboboxes
        self.range_combo.addItems(Const.VALID_IMP_RANGES)
        self.function_combo.addItems(list(Const.FUNC_DICT.keys()))
        self.measuring_time_combo.addItems(list(Const.MEASURE_TIME_DICT.keys()))
        self.signal_type_combo.addItems(['Voltage', 'Current'])
        self.bias_type_combo.addItems(['Voltage', 'Current'])

        # Set up tool buttons
        save_icon_path = Path('src/img').absolute() / 'save.svg'
        run_icon_path = Path('src/img').absolute() / 'run.svg'
        stop_icon_path = Path('src/img').absolute() / 'stop.svg'
        self.save_icon.addFile(str(save_icon_path))
        self.run_icon.addFile(str(run_icon_path))
        self.stop_icon.addFile(str(stop_icon_path))

        self.save_file_btn.setIcon(self.save_icon)
        self.run_start_meas_btn.setIcon(self.run_icon)
        self.run_start_meas_btn.setIconSize(QSize(60, 60))
        self.run_start_meas_btn.setFont(FormatLib.RUN_BTN_FONT)
        self.run_start_meas_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.run_start_meas_btn.setText('Run Measurement Set')

        self.setup_start_meas_btn.setIcon(self.run_icon)
        self.setup_start_meas_btn.setIconSize(QSize(60, 60))
        self.setup_start_meas_btn.setFont(FormatLib.RUN_BTN_FONT)
        self.setup_start_meas_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setup_start_meas_btn.setText('Run Measurement Set')

        # Set up live readout labels
        self.val1_lbl.setStyleSheet(FormatLib.LIVE_VAL_LBL_STYLE)
        self.val1_lbl.setFrameStyle(QFrame.Raised)
        self.val2_lbl.setStyleSheet(FormatLib.LIVE_VAL_LBL_STYLE)
        self.val2_lbl.setFrameStyle(QFrame.Sunken)
        self.val2_lbl.setLineWidth(3)

        # Set up timers
        self.live_readout_timer.start(500)

        # Set up progress bar
        self.meas_progress_bar.setOrientation(Qt.Horizontal)
        self.meas_progress_bar.setTextVisible(True)
        # self.setMinimumHeight(60)
        self.meas_progress_lbl.setAlignment(Qt.AlignCenter)

    def init_layout(self):
        config_width = 325

        # Set widget geometry
        # self.sizePolicy().setHeightForWidth(True)
        # self.setMinimumSize(1600, 900)

        # Initialize the hbox to hold the save file info
        save_file_hbox = QHBoxLayout()
        save_file_hbox.addWidget(self.save_file_ln)
        save_file_hbox.addWidget(self.save_file_btn)

        # Initialize the form layout for the measuring parameters
        measuring_param_form = QFormLayout()
        measuring_param_form.addRow('Measuring Function:', self.function_combo)
        measuring_param_form.addRow('Measuring Time:', self.measuring_time_combo)
        measuring_param_form.addRow('Data Averaging:', self.measuring_avg_ln)
        measuring_param_form.addRow('# of Data Points:', self.num_data_pts_ln)
        measuring_param_form.addRow('Delay Between Steps:', self.step_delay_ln)
        measuring_param_form.addRow('Impedance Range:', self.range_combo)
        measuring_param_form.addRow('Signal Type:', self.signal_type_combo)
        measuring_param_form.addRow('DC Bias Type:', self.bias_type_combo)
        measuring_param_form.addRow('Sample Memo:', self.notes)
        measuring_param_form.addRow('Save File To:', save_file_hbox)

        # Combine the form and hbox to finish the measuring parameter control layout
        measuring_param_vbox = QVBoxLayout()
        measuring_param_vbox.addLayout(measuring_param_form)
        measuring_param_vbox.addLayout(save_file_hbox)

        # Set the measuring param layout to the measuring param group box
        self.measuring_param_box.setLayout(measuring_param_vbox)
        # self.measuring_param_box.setFixedWidth(config_width)

        ###
        # Initialize the measurement setup form for number of measurements
        meas_setup_form = QFormLayout()
        meas_setup_form.addRow('Number of Measurements:', self.num_measurements_ln)

        # Add the form and table to the vertical layout
        meas_setup_vbox = QVBoxLayout()
        meas_setup_vbox.addLayout(meas_setup_form)
        meas_setup_vbox.addWidget(self.meas_setup_table)

        # Set the layout of the measurement setup box
        self.meas_setup_box.setLayout(meas_setup_vbox)
        # self.meas_setup_box.setFixedWidth(config_width)

        ###
        # Initialize config layout
        config_controls_vbox = QVBoxLayout()
        config_controls_vbox.addWidget(self.measuring_param_box)
        config_controls_vbox.addWidget(self.meas_setup_box)
        config_controls_vbox.addWidget(self.setup_start_meas_btn)
        config_controls_vbox.setAlignment(self.setup_start_meas_btn, Qt.AlignHCenter)
        self.meas_setup_tab.setLayout(config_controls_vbox)

        ###
        # Initialize the sublayouts for the running measurement
        curr_meas_hbox = QHBoxLayout()
        curr_meas_hbox.addWidget(QLabel('Start:'), 10)
        curr_meas_hbox.addWidget(self.curr_meas_start, 10)
        curr_meas_hbox.addWidget(QLabel('  |  '), 10)
        curr_meas_hbox.addWidget(QLabel('Stop:'), 10)
        curr_meas_hbox.addWidget(self.curr_meas_stop, 10)
        curr_meas_hbox.addWidget(QLabel('  |  '), 10)
        curr_meas_hbox.addWidget(QLabel('Oscillator:'), 10)
        curr_meas_hbox.addWidget(self.curr_meas_osc, 10)
        curr_meas_hbox.addWidget(QLabel('  |  '), 10)
        curr_meas_hbox.addWidget(QLabel('Bias:'), 10)
        curr_meas_hbox.addWidget(self.curr_meas_bias, 10)

        curr_meas_groupbox = QGroupBox()
        curr_meas_groupbox.setTitle('Current Measurement Parameters:')
        curr_meas_groupbox.setLayout(curr_meas_hbox)

        val1_vbox = QVBoxLayout()
        val1_vbox.addWidget(self.val1_lbl, 10)
        val1_vbox.addWidget(self.val1_live_plot, 90)
        self.val1_frame.setLayout(val1_vbox)

        val2_vbox = QVBoxLayout()
        val2_vbox.addWidget(self.val2_lbl, 10)
        val2_vbox.addWidget(self.val2_live_plot, 90)
        self.val2_frame.setLayout(val2_vbox)

        # Combine val1 and val2 sublayouts
        vals_hbox = QHBoxLayout()
        vals_hbox.addWidget(self.val1_frame, 50)
        vals_hbox.addWidget(self.val2_frame, 50)

        # Initialize sublayouts for the progress information
        progress_vbox = QVBoxLayout()
        progress_vbox.addWidget(curr_meas_groupbox)
        progress_vbox.addWidget(self.meas_progress_bar)

        progress_hbox = QHBoxLayout()
        progress_hbox.addWidget(self.run_start_meas_btn, 20)
        progress_hbox.addLayout(progress_vbox, 70)
        progress_hbox.addWidget(self.meas_progress_lbl, 10)
        # progress_hbox.setAlignment(Qt.AlignBottom)

        vals_vbox = QVBoxLayout()
        vals_vbox.addLayout(vals_hbox)
        vals_vbox.addLayout(progress_hbox)
        self.meas_run_tab.setLayout(vals_vbox)

        ###
        # Set up overall widget layout
        # overall_hbox = QHBoxLayout()
        # overall_hbox.addLayout(config_controls_vbox)
        # overall_hbox.addLayout(vals_vbox)
        # self.setLayout(overall_hbox)
        self.addTab(self.meas_setup_tab, 'Measurement Setup')
        self.addTab(self.meas_run_tab, 'Run Measurement')

    def print_size(self):
        print('Measuring Params:', self.measuring_param_box.size(), sep=' ')
        print('Measurement setup:', self.meas_setup_box.size(), sep=' ')

    def change_function(self):
        self.lcr_function = self.function_combo.currentText()
        self.update_val_labels()

    def change_meas_aperture(self):
        self.measuring_time = self.measuring_time_combo.currentText()
        try:
            self.measuring_avg = int(self.measuring_avg_ln.text())
        except ValueError:
            self.measuring_avg = 1
            self.measuring_avg_ln.setText(str(self.measuring_avg))

    def change_num_pts(self):
        try:
            self.num_data_pts = int(self.num_data_pts_ln.text())
        except ValueError:
            self.num_data_pts = 50
            self.num_data_pts_ln.setText(str(self.num_data_pts))

    def change_step_delay(self):
        try:
            self.step_delay = float(self.step_delay_ln.text())
        except ValueError:
            self.step_delay = 0.0
            self.step_delay_ln.setText(str(self.step_delay))

    def change_impedance_range(self):
        self.range = self.range_combo.currentText()

    def change_signal_type(self):
        self.signal_type = self.signal_type_combo.currentText()

    def change_bias_type(self):
        self.bias_type = self.bias_type_combo.currentText()

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

        self.save_file_ln.setText(self.save_file_path)

    def set_save_file_path_by_text(self):
        self.save_file_path = self.save_file_ln.text()

    def change_num_measurements(self):
        num = self.num_measurements
        try:
            self.num_measurements = int(self.num_measurements_ln.text())
        except ValueError:
            self.num_measurements = num

        self.meas_setup_table.setRowCount(self.num_measurements)
        self.update_table_vheaders()
        self.add_table_items()

    def update_live_readout(self, data: list):

        self.val1_lbl.setText(str(Static.to_sigfigs(data[1], 6)))
        self.val2_lbl.setText(str(Static.to_sigfigs(data[2], 6)))

    def update_table_hheaders(self):
        self.meas_setup_table.setHorizontalHeaderLabels(self.meas_setup_hheaders)

    def update_table_vheaders(self):
        self.meas_setup_vheaders = ['M{}'.format(x) for x in range(1, self.num_measurements + 1)]
        self.meas_setup_table.setVerticalHeaderLabels(self.meas_setup_vheaders)

    def add_table_items(self):
        for irow in range(0, self.meas_setup_table.rowCount()):
            for icol in range(0, self.meas_setup_table.columnCount()):
                widget = self.meas_setup_table.item(irow, icol)
                # If the cell doesn't already have a QTableWidgetItem
                if widget is None:
                    # Create a new QTableWidgetItem in the cell
                    new_widget = QTableWidgetItem()
                    if irow > 0:
                        # Get the value of the cell above
                        value = self.meas_setup_table.item(irow-1, icol).text()
                        new_widget.setText(value)
                    # Put the new widget in the table
                    self.meas_setup_table.setItem(irow, icol, new_widget)

    def generate_header(self, index, row):
        # Gather format strings for header
        meas_number = index
        now = datetime.now()
        date_now = str(now).split(' ')[0]
        time_now = str(now.strftime('%H:%M:%S'))

        start = row[self.meas_setup_hheaders[0]]
        stop = row[self.meas_setup_hheaders[1]]

        osc = row[self.meas_setup_hheaders[2]]
        if self.signal_type_combo.currentText() == 'Voltage':
            osc_type = 'V'
        elif self.signal_type_combo.currentText() == 'Current':
            osc_type = 'A'
        else:
            osc_type = 'UNKNOWN'

        bias = row[self.meas_setup_hheaders[3]]
        if self.bias_type_combo.currentText() == 'Voltage':
            bias_type = 'V'
        elif self.bias_type_combo.currentText() == 'Current':
            bias_type = 'A'
        else:
            bias_type = 'UNKNOWN'

        notes = self.notes.text()

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

        for irow in range(0, self.meas_setup_table.rowCount()):
            for icol in range(0, self.meas_setup_table.columnCount()):
                self.tests_df.iloc[irow, icol] = self.meas_setup_table.item(irow, icol).text()

    def enable_controls(self, enable: bool):
        self.meas_setup_box.setEnabled(enable)
        self.measuring_param_box.setEnabled(enable)

    def enable_live_val_timer(self, enable: bool):
        try:
            if enable:
                self.live_readout_timer.timeout.connect(self.lcr.get_data)
            elif not enable:
                self.live_readout_timer.timeout.disconnect(self.lcr.get_data)
        except TypeError:
            print('Unable to disconnect or reconnect live value timer correctly')

    def enable_live_plots(self, enable: bool):
        if enable:
            try:
                self.lcr.new_data.connect(self.plot_new_points)
            except TypeError:
                pass
        elif not enable:
            try:
                self.lcr.new_data.disconnect(self.plot_new_points)
            except TypeError:
                pass

    def setup_lcr(self):
        self.lcr.function(self.lcr_function)
        self.lcr.impedance_range(self.range)
        self.lcr.measurement_aperture(self.measuring_time, self.measuring_avg)
        self.lcr.signal_level(self.signal_type, self.meas_setup_table.item(0, 2).text())
        self.lcr.dc_bias_level(self.bias_type, self.meas_setup_table.item(0, 3).text())

    def change_start_button(self):
        if self.run_start_meas_btn.text() == 'Run Measurement Set':
            self.run_start_meas_btn.setText('Stop Measuring')
            self.run_start_meas_btn.setIcon(self.stop_icon)
            self.run_start_meas_btn.clicked.disconnect(self.start_measurement)
            self.run_start_meas_btn.clicked.connect(self.halt_measurement)

            self.setup_start_meas_btn.setText('Stop Measuring')
            self.setup_start_meas_btn.setIcon(self.stop_icon)
            self.setup_start_meas_btn.clicked.disconnect(self.start_measurement)
            self.setup_start_meas_btn.clicked.connect(self.halt_measurement)
        elif self.run_start_meas_btn.text() == 'Stop Measuring':
            self.run_start_meas_btn.setText('Run Measurement Set')
            self.run_start_meas_btn.setIcon(self.run_icon)

            self.setup_start_meas_btn.setText('Run Measurement Set')
            self.setup_start_meas_btn.setIcon(self.run_icon)

    def halt_measurement(self):
        self.stop_measurement_worker.emit()

    def start_measurement(self):
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
        elif self.save_file_path == os.path.join(os.getenv('USERPROFILE'), 'Desktop'):
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

        # FIXME: Make the measurement start button turn into a stop button (will require a new signal and code
        #        in the measurement worker). Should it just dump the data?
        self.change_start_button()
        self.setCurrentWidget(self.meas_run_tab)
        # Set up the progress bar for this measurement
        self.meas_progress_bar.setMinimum(0)
        self.meas_progress_bar.setMaximum(self.num_measurements * self.num_data_pts)
        self.meas_progress_bar.reset()
        # Keep the user from changing values in the controls
        self.enable_controls(False)
        # Set live vals to update to last read value only
        self.enable_live_val_timer(False)
        # Enable live plotting of values, clear previous data
        self.enable_live_plots(True)
        self.val1_live_plot.clear_data()
        self.val2_live_plot.clear_data()

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
        self.enable_live_plots(False)
        self.return_to_defaults()

        print('Measurement finished')
        self.change_start_button()
        try:
            self.run_start_meas_btn.clicked.connect(self.start_measurement)
            self.run_start_meas_btn.clicked.disconnect(self.halt_measurement)

            self.setup_start_meas_btn.clicked.connect(self.start_measurement)
            self.setup_start_meas_btn.clicked.disconnect(self.halt_measurement)
        except TypeError:
            print('changing connections failed')

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
        self.val1_live_plot.add_data([data[0], data[1]])
        self.val2_live_plot.add_data([data[0], data[2]])

    def update_val_labels(self):
        val_params = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.lcr_function]]
        self.val1_live_plot.update_plot_labels(['Frequency [Hz]', val_params[0]])
        self.val1_frame.setTitle(val_params[0])
        self.val2_live_plot.update_plot_labels(['Frequency [Hz]', val_params[1]])
        self.val2_frame.setTitle(val_params[1])

    def update_measurement_progress(self, indices: list):
        # NOTE: indices[0] will be the measurement number (one indexed), and
        # indices[1] will be the step number (Zero indexed)
        self.meas_progress_bar.setValue(((indices[0] - 1) * self.num_data_pts) + (indices[1] + 1))
        self.meas_progress_lbl.setText('Measurement {}/{},\nStep {}/{}'.format(indices[0], self.num_measurements,
                                                                               indices[1] + 1, self.num_data_pts))


class MeasureWorkerObj (QObject):
    measurement_finished = pyqtSignal()
    freq_step_finished = pyqtSignal(list)

    def __init__(self, parent: CapFreqWidget, lcr: AgilentE4980A):
        super().__init__()
        self.parent = parent
        self.stop = False
        self.parent.stop_measurement_worker.connect(self.stop_early)

    def stop_early(self):
        self.stop = True

    def set_current_meas_labels(self, start, stop, osc, bias):
        self.parent.curr_meas_start.setText(str(start))
        self.parent.curr_meas_stop.setText(str(stop))
        self.parent.curr_meas_osc.setText(str(osc))
        self.parent.curr_meas_bias.setText(str(bias))

    def measure(self):
        # Write configured parameters to lcr
        self.parent.setup_lcr()

        # Generate the matrix of tests to run
        self.parent.generate_test_matrix()

        # Set up the data column headers
        columns = Const.PARAMETERS_BY_FUNC[Const.FUNC_DICT[self.parent.function_combo.currentText()]]
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
            self.parent.lcr.signal_level(self.parent.signal_type_combo.currentText(), osc)
            self.parent.lcr.dc_bias_level(self.parent.bias_type_combo.currentText(), bias)

            freq_steps = Static.generate_log_steps(int(start), int(stop), int(self.parent.num_data_pts))

            # Start a new data line in each plot
            self.parent.val1_live_plot.live_plot.start_new_line()
            self.parent.val2_live_plot.live_plot.start_new_line()

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
