import visa
from pyvisa.errors import VisaIOError
from PyQt5.QtWidgets import QDialog, QComboBox, QPushButton, QFormLayout, QLabel


# General class to allow selection of visa resources
class InstrumentSelectBox (QDialog):
    def __init__(self, rm: visa.ResourceManager):
        super().__init__()

        self.rm = rm
        # Get a list of resources, open comms, and poll them for their ID string
        self.instruments = rm.list_resources()
        self.instr_ids = []

        for instr in self.instruments:
            current_instr = self.rm.open_resource(instr)
            try:
                self.instr_ids.append(current_instr.query("*IDN?"))
            except VisaIOError:
                print('Error getting instrument ID string from {}'.format(instr))
            current_instr.close()

        self.instr_combo_box = QComboBox()
        self.instr_combo_box.addItems(self.instruments)
        self.instr_id_label = QLabel()
        self.ok_btn = QPushButton('Ok')

        self.form_layout = QFormLayout()

        self.init_layout()
        self.init_connections()

    def init_layout(self):
        self.form_layout.addRow('Select an instrument:', self.instr_combo_box)
        self.form_layout.addRow('Instrument ID:', self.instr_id_label)
        self.form_layout.addRow('', self.ok_btn)

        self.setLayout(self.form_layout)

    def init_connections(self):
        self.instr_combo_box.currentTextChanged.connect(self.update_id_label)
        self.ok_btn.clicked.connect(self.accept)

    def update_id_label(self):
        # Change the label to reflect the newly selected combobox item
        self.instr_id_label.setText(self.instr_ids[self.instr_combo_box.currentIndex()])