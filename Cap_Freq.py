from PyQt5.QtWidgets import (QWidget, QComboBox, QLineEdit, QLabel, QFormLayout, QVBoxLayout,
                             QGroupBox, QTableWidget, QTableWidgetItem, QHBoxLayout,
                             QToolButton, QApplication, QFileDialog, QFrame)
from PyQt5.QtCore import QTimer, QThread, Qt
import sys
import os
from io import StringIO
import pandas as pd
import numpy as np
from datetime import datetime
from Live_Data_Plotter import LivePlotWidget
# from Agilent_E4980A import AgilentE4980A
from fake_E4980 import AgilentE4980A
from Agilent_E4980A_Constants import *
from File_Print_Headers import *


class CapFreqWidget (QWidget):
    def __init__(self, lcr: AgilentE4980A):
        super().__init__()

        # Define class variables and objects
        self.lcr = lcr
        self.num_data_pts = 50
        self.measuring_avg = 1
        self.num_measurements = 1
        self.frequency = self.lcr.get_signal_frequency()
        self.tests_df = pd.DataFrame()
        self.save_file_path = os.path.join(os.getenv('USERPROFILE'), 'Desktop')

        # Create a thread to hold the instrument class as a worker
        self.instr_thread = QThread()
        self.lcr.moveToThread(self.instr_thread)

        # Define controls for the overall measuring parameters
        self.measuring_param_box = QGroupBox('Measuring Parameters:')
        self.function_combo = QComboBox()
        self.measuring_time_combo = QComboBox()
        self.range_combo = QComboBox()
        self.measuring_avg_ln = QLineEdit(str(self.measuring_avg))
        self.signal_type_combo = QComboBox()
        self.bias_type_combo = QComboBox()
        self.num_data_pts_ln = QLineEdit(str(self.num_data_pts))
        self.notes = QLineEdit()
        self.save_file_ln = QLineEdit()
        self.save_file_btn = QToolButton()

        # Define controls for the per measurement settings
        self.meas_setup_box = QGroupBox('Measurement(s) Setup:')
        self.num_measurements_ln = QLineEdit(str(self.num_measurements))
        self.meas_setup_table = QTableWidget()
        self.meas_setup_hheaders = ['Frequency\nStart [Hz]', 'Frequency\nStop [Hz]', 'Oscillator [V]', 'DC Bias [V]']
        self.meas_setup_vheaders = ['M1', 'M2', 'M3', 'M4']

        # Define stuff for live plotting and value readout
        self.val1_frame = QFrame()
        self.val1_lbl = QLabel()
        self.val1_live_plot = LivePlotWidget(['Frequency [Hz]', 'val_params[0]'],
                                             lead=False,
                                             head=True,
                                             draw_interval=350)
        self.val2_frame = QFrame()
        self.val2_lbl = QLabel()
        self.val2_live_plot = LivePlotWidget(['Frequency [Hz]', 'val_params[1]'],
                                             lead=False,
                                             head=True,
                                             draw_interval=350)
        self.update_live_readout()
        self.live_readout_timer = QTimer()
        self.start_meas_btn = QToolButton()

        # Define layouts that need to stay available after widget init
        self.config_controls_vbox = QVBoxLayout()

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()
        self.init_layout()

    def init_connections(self):
        # Instrument
        self.lcr.new_data.connect(self.plot_new_points)

        # Control edit connections
        self.function_combo.currentTextChanged.connect(self.change_function)
        self.measuring_time_combo.currentTextChanged.connect(self.change_meas_aperture)
        self.measuring_avg_ln.editingFinished.connect(self.change_meas_aperture)
        self.num_data_pts_ln.editingFinished.connect(self.change_num_pts)
        self.range_combo.currentTextChanged.connect(self.change_impedance_range)
        self.signal_type_combo.currentTextChanged.connect(self.change_signal_type)
        self.bias_type_combo.currentTextChanged.connect(self.change_bias_type)
        self.save_file_ln.editingFinished.connect(self.check_entered_filepath)
        self.save_file_btn.clicked.connect(self.open_save_dialog)
        self.save_file_btn.clicked.connect(self.print_size)
        self.num_measurements_ln.editingFinished.connect(self.change_num_measurements)
        self.start_meas_btn.clicked.connect(self.measure)

        # Timers
        self.live_readout_timer.timeout.connect(self.update_live_readout)

    def init_control_setup(self):
        # Set up initial table headers and size
        self.meas_setup_table.setRowCount(1)
        self.meas_setup_table.setColumnCount(4)
        self.meas_setup_table.setHorizontalHeaderLabels(self.meas_setup_hheaders)
        self.meas_setup_table.setVerticalHeaderLabels(self.meas_setup_vheaders)
        self.meas_setup_table.setWordWrap(True)
        self.meas_setup_table.resizeColumnsToContents()
        self.add_table_items()
        self.meas_setup_table.item(0, 0).setText('1e6')
        self.meas_setup_table.item(0, 1).setText('20')
        self.meas_setup_table.item(0, 2).setText('0.05')
        self.meas_setup_table.item(0, 3).setText('0')

        # Set up comboboxes
        self.range_combo.addItems(VALID_IMP_RANGES)
        self.function_combo.addItems(list(FUNC_DICT.keys()))
        self.measuring_time_combo.addItems(list(MEASURE_TIME_DICT.keys()))
        self.signal_type_combo.addItems(['Voltage', 'Current'])
        self.bias_type_combo.addItems(['Voltage', 'Current'])

        # Set up live readout labels
        live_data_lbl_stylesheet = 'QLabel {font-weight: bold; color: black; font-size: 150px; background-color: grey}'
        self.val1_lbl.setStyleSheet(live_data_lbl_stylesheet)
        self.val2_lbl.setStyleSheet(live_data_lbl_stylesheet)

        # Set up timers
        self.live_readout_timer.start(500)

        # Update live readouts
        self.update_live_readout()

    def init_layout(self):
        config_width = 706

        # Set widget geometry
        self.sizePolicy().setHeightForWidth(True)
        self.setMinimumSize(1920, 1080)

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
        self.measuring_param_box.setFixedSize(config_width, 445)

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
        self.meas_setup_box.setFixedWidth(config_width)

        ###
        # Initialize config layout
        self.config_controls_vbox.addWidget(self.measuring_param_box)
        self.config_controls_vbox.addWidget(self.meas_setup_box)
        self.config_controls_vbox.addWidget(self.start_meas_btn)

        ###
        # Initialize the live values layouts
        val1_vbox = QVBoxLayout()
        val1_vbox.addWidget(self.val1_lbl)
        val1_vbox.addWidget(self.val1_live_plot)
        self.val1_frame.setLayout(val1_vbox)

        val2_vbox = QVBoxLayout()
        val2_vbox.addWidget(self.val2_lbl)
        val2_vbox.addWidget(self.val2_live_plot)
        self.val2_frame.setLayout(val2_vbox)

        vals_hbox = QHBoxLayout()
        vals_hbox.addWidget(self.val1_frame)
        vals_hbox.addWidget(self.val2_frame)

        ###
        # Set overall layout up
        overall_hbox = QHBoxLayout()
        overall_hbox.addLayout(self.config_controls_vbox)
        overall_hbox.addLayout(vals_hbox)
        self.setLayout(overall_hbox)

    def print_size(self):
        print('Measuring Params:', self.measuring_param_box.size(), sep=' ')
        print('Measurement setup:', self.meas_setup_box.size(), sep=' ')

    def change_function(self):
        self.lcr.function(self.function_combo.currentText())
        self.update_val_labels()

    def change_meas_aperture(self):
        self.lcr.measurement_aperture(self.measuring_time_combo.currentText(), self.measuring_avg_ln.text())

    def change_num_pts(self):
        self.num_data_pts = int(self.num_data_pts_ln.text())

    def change_impedance_range(self):
        self.lcr.impedance_range(self.range_combo.currentText())

    def change_signal_type(self):
        signal_type = self.signal_type_combo.currentText()
        self.lcr.signal_level(signal_type, self.meas_setup_table.item(0, 2).text())

    def change_bias_type(self):
        bias_type = self.bias_type_combo.currentText()
        self.lcr.dc_bias_level(bias_type, self.meas_setup_table.item(0, 3).text())

    def open_save_dialog(self):
        file_name = QFileDialog.getSaveFileName(self,
                                                'Select a file to save data...',
                                                self.save_file_path,
                                                "All Types (*)")
        self.save_file_path = file_name[0]
        self.save_file_ln.setText(self.save_file_path)
        self.print_size()

    def check_entered_filepath(self):
        self.save_file_path = self.save_file_ln.text()

    def change_num_measurements(self):
        self.num_measurements = int(self.num_measurements_ln.text())
        self.meas_setup_table.setRowCount(self.num_measurements)
        self.update_table_vheaders()
        self.add_table_items()

    def update_live_readout(self):
        vals = self.lcr.get_data()
        self.val1_lbl.setText(vals[0])
        self.val2_lbl.setText(vals[1])

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
                    self.meas_setup_table.setItem(irow, icol, QTableWidgetItem())

    def generate_header(self, index, row):
        # Gather format strings for header
        meas_type = self.function_combo.currentText()
        meas_number = index
        now = datetime.now()
        date = str(now).split(' ')[0]
        time = str(now.strftime('%H:%M:%S'))

        start = row[self.meas_setup_hheaders[0]]
        stop = row[self.meas_setup_hheaders[1]]

        osc = row[self.meas_setup_hheaders[2]]
        if self.signal_type_combo.currentText() == 'Voltage':
            osc_type = 'V'
        elif self.signal_type_combo.currentText() == 'Current':
            osc_type = 'A'

        bias = row[self.meas_setup_hheaders[3]]
        if self.bias_type_combo.currentText() == 'Voltage':
            bias_type = 'V'
        elif self.bias_type_combo.currentText() == 'Current':
            bias_type = 'A'

        notes = self.notes.text()

        header = CAP_FREQ_HEADER.format(meas_type,
                                        date,
                                        time,
                                        meas_number,
                                        start,
                                        stop,
                                        osc_type, osc,
                                        bias_type, bias,
                                        'Notes: {}'.format(notes))

        return header

    def generate_test_matrix(self):
        self.tests_df = pd.DataFrame(data=None, index=self.meas_setup_vheaders, columns=self.meas_setup_hheaders)

        for irow in range(0, self.meas_setup_table.rowCount()):
            for icol in range(0, self.meas_setup_table.columnCount()):
                self.tests_df.iloc[irow, icol] = self.meas_setup_table.item(irow, icol).text()

        print(self.tests_df)

    def enable_controls(self, enable: bool):
        for widget in self.config_controls_vbox.findChildren(QWidget):
            widget.setEnabled(enable)

    def measure(self):
        self.enable_controls(False)
        self.generate_test_matrix()

        # Check if any of the DC bias values are non-zero, and turn the bias function on or off accordingly
        for bias in self.tests_df[self.meas_setup_hheaders[2]]:
            if float(bias) != 0:
                self.lcr.dc_bias_state('on')
                break
            self.lcr.dc_bias_state('off')

        # For each measurement in the test matrix
        for index, row in self.tests_df.iterrows():
            # Create an empty data frame to hold results, Index=M1-Mn, Column Headers determined by measurement type
            data_df = pd.DataFrame(data=None,
                                   index=self.meas_setup_vheaders,
                                   columns=PARAMETERS_BY_FUNC[FUNC_DICT[self.function_combo.currentText()]])

            # Pull in test specific values
            start = row[self.meas_setup_hheaders[0]]
            stop = row[self.meas_setup_hheaders[1]]
            osc = row[self.meas_setup_hheaders[2]]
            bias = row[self.meas_setup_hheaders[3]]

            # Set lcr accordingly
            self.lcr.signal_level(self.signal_type_combo.currentText(), osc)
            self.lcr.dc_bias_level(self.bias_type_combo.currentText(), bias)

            # TODO: Generate steps
            freq_steps = self.generate_log_steps(start, stop, self.num_data_pts)

            for freq_step in freq_steps:
                # Set the lcr to the correct frequency
                self.lcr.signal_frequency(freq_step)

                # Trigger the measurement to start
                self.lcr.trigger_init()

                # Read the measurement result
                data = self.lcr.get_data()

                # Store the data do the data_df
                data_df[index].iloc[0] = freq_step
                data_df[index].iloc[1] = data[0]
                data_df[index].iloc[2] = data[1]

            # Store the measurement data in a field of the tests_df
            self.tests_df[index]['Header'] = self.generate_header(index, row)
            self.tests_df[index]['Data'] = data_df

        self.save_data()

    def save_data(self):
        ram_csv = StringIO()
        with open(self.save_file_path, 'w') as file:
            for index, row in self.tests_df.iterrows():
                file.write(row['Header'])
                row['Data'].to_csv(ram_csv,
                                   sep='\t')
                file.write('\n')
                file.write(ram_csv.getvalue())

        ram_csv.close()

    def generate_log_steps(self, start, stop, num_steps):
        step = 10 ** ((np.log10(stop)-np.log10(start)) / (num_steps-1))
        freq_steps = [start * (step ** i) for i in range(0, num_steps-1)]
        freq_steps.append(stop)

        return freq_steps

    def plot_new_points(self, data: list):
        self.val1_live_plot.add_data([self.frequency, data[0]])
        self.val2_live_plot.add_data([self.frequency, data[1]])

    def update_val_labels(self):
        val_params = PARAMETERS_BY_FUNC[FUNC_DICT[self.function_combo.currentText()]]
        self.val1_live_plot.update_plot_labels(['Frequency [Hz]', val_params[0]])
        self.val2_live_plot.update_plot_labels(['Frequency [Hz]', val_params[1]])


app = QApplication(sys.argv)
gui = CapFreqWidget(AgilentE4980A())
gui.show()

sys.exit(app.exec_())