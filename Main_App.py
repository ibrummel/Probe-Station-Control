import sys

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
import visa
from pyvisa.errors import VisaIOError
from Agilent_E4980A import AgilentE4980A
from Sun_EC1X import SunEC1xChamber
from Cap_Freq import CapFreqWidget
from Cap_Freq_Temp import CapFreqTempWidget


class ProbeStationControlMainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.instruments = {'lcr': 'GPIB0::18::INSTR',
                            'sun': 'GPIB0::6::INSTR',
                            'src_meas': 'NOT USED',
                            'electrometer': 'NOT USED'}

        self.rm = visa.ResourceManager()

        # Connect to instruments, eventually replace with the dialog to set ID strings
        self.instruments['lcr'] = AgilentE4980A(parent=self, gpib_addr=self.instruments['lcr'])
        self.instruments['sun'] = SunEC1xChamber(parent=self, gpib_addr=self.instruments['sun'])
        # Add connections to other instruments as needed.

        # Create a thread for all the measuring widgets to use
        self.measuring_thread = QThread()

        self.cap_freq = CapFreqWidget(lcr=self.instruments['lcr'])
        self.cap_freq_temp = CapFreqTempWidget(lcr=self.instruments['lcr'], sun=self.instruments['sun'])

        self.tabs_meas_types = QTabWidget()
        self.tabs_meas_types.addTab(self.cap_freq, 'Capacitance-Frequency')
        self.tabs_meas_types.addTab(self.cap_freq_temp, 'Capacitance-Frequency-Temperature')

        self.setCentralWidget(self.tabs_meas_types)


app = QApplication(sys.argv)

main_window = ProbeStationControlMainWindow()
main_window.show()
sys.exit(app.exec_())

