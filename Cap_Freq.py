from PyQt5.QtWidgets import (QWidget, QComboBox, QLineEdit, QLabel, QFormLayout, QVBoxLayout,
                             QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem, QHBoxLayout,
                             QToolButton, QApplication, QFileDialog, QMessageBox)
import sys
import os
import pandas as pd
# from Agilent_E4980A import AgilentE4980A
from fake_E4980 import AgilentE4980A
from Agilent_E4980A_Constants import *

class CapFreqWidget (QWidget):
    def __init__(self, lcr: AgilentE4980A):
        super().__init__()

        # Define class variables and objects
        self.lcr = lcr
        self.num_data_pts = 50
        self.measuring_avg = 1
        self.num_measurements = 1
        self.save_file_path = os.path.join(os.getenv('USERPROFILE'), 'Desktop')

        # Define controls for the overall measuring parameters
        self.measuring_param_box = QGroupBox('Measuring Parameters:')
        self.function_combo = QComboBox()
        self.measuring_time_combo = QComboBox()
        self.range_combo = QComboBox()
        self.measuring_avg_ln = QLineEdit(str(self.measuring_avg))
        self.signal_type_combo = QComboBox()
        self.num_data_pts_ln = QLineEdit(str(self.num_data_pts))
        self.save_file_ln = QLineEdit()
        self.save_file_btn = QToolButton()

        # Define controls for the per measurement settings
        self.meas_setup_box = QGroupBox('Measurement(s) Setup:')
        self.num_measurements_ln = QLineEdit(str(self.num_measurements))
        self.meas_setup_table = QTableWidget()
        self.meas_setup_hheaders = ['Frequency\nStart [Hz]', 'Frequency\nStop [Hz]', 'Oscillator [V]', 'DC Bias [V]']
        self.meas_setup_vheaders = ['M1', 'M2', 'M3', 'M4']

        # Initialize widget bits
        self.init_connections()
        self.init_control_setup()
        self.init_layout()

    def init_connections(self):
        self.function_combo.currentTextChanged.connect(self.change_function)
        self.measuring_time_combo.currentTextChanged.connect(self.change_meas_aperture)
        self.measuring_avg_ln.editingFinished.connect(self.change_meas_aperture)
        self.num_data_pts_ln.editingFinished.connect(self.change_num_pts)
        self.range_combo.currentTextChanged.connect(self.change_impedance_range)
        self.signal_type_combo.currentTextChanged.connect(self.change_signal_type)
        self.save_file_ln.editingFinished.connect(self.check_entered_filepath)
        self.save_file_btn.clicked.connect(self.open_save_dialog)
        self.num_measurements_ln.editingFinished.connect(self.change_num_measurements)

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

    def init_layout(self):
        setup_width = 706
        setup_height = 360

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
        measuring_param_form.addRow('Save File To:', save_file_hbox)

        # Combine the form and hbox to finish the measuring parameter control layout
        measuring_param_vbox = QVBoxLayout()
        measuring_param_vbox.addLayout(measuring_param_form)
        measuring_param_vbox.addLayout(save_file_hbox)

        # Set the measuring param layout to the measuring param group box
        self.measuring_param_box.setLayout(measuring_param_vbox)
        self.measuring_param_box.setFixedSize(setup_width, setup_height)

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
        self.meas_setup_box.setFixedSize(setup_width, 495)

        ###
        # Initialize config layout
        config_controls_vbox = QVBoxLayout()
        config_controls_vbox.addWidget(self.measuring_param_box)
        config_controls_vbox.addWidget(self.meas_setup_box)

        # FIXME: Set layout to be the config controls
        self.setLayout(config_controls_vbox)

    def print_size(self):
        print('Measuring Params:', self.measuring_param_box.size(), sep=' ')
        print('Measurement setup:', self.meas_setup_box.size(), sep=' ')

    def change_function(self):
        self.lcr.function(self.function_combo.currentText())

    def change_meas_aperture(self):
        self.lcr.measurement_aperture(self.measuring_time_combo.currentText(), self.measuring_avg_ln.text())

    def change_num_pts(self):
        self.num_data_pts = int(self.num_data_pts_ln.text())

    def change_impedance_range(self):
        self.lcr.impedance_range(self.range_combo.currentText())

    def change_signal_type(self):
        signal = self.signal_type_combo.currentText()

        if signal == 'Voltage':
            self.meas_setup_hheaders[2] = 'Oscillator [V]'
            self.update_table_hheaders()
            self.lcr.signal_voltage(self.meas_setup_table.item(0, 2).text())
        elif signal == 'Current':
            self.meas_setup_hheaders[2] = 'Oscillator [A]'
            self.update_table_hheaders()
            self.lcr.signal_current(self.meas_setup_table.item(0, 2).text())

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

    def generate_header(self):
        pass

    def generate_test_matrix(self):
        tests_df = pd.DataFrame(data=None, index=self.meas_setup_vheaders, columns=self.meas_setup_hheaders)

        for irow in range(0, self.meas_setup_table.rowCount()):
            for icol in range(0, self.meas_setup_table.columnCount()):
                tests_df.iloc[irow, icol] = self.meas_setup_table.item(irow, icol).text()

        print(tests_df)


    def measure(self):
        pass

app = QApplication(sys.argv)
gui = CapFreqWidget(AgilentE4980A())
gui.show()

sys.exit(app.exec_())