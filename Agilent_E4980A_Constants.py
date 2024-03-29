ID_STR = 'Agilent Technologies,E4980A,'

VALID_FUNCTIONS = ['CPD', 'CPQ', 'CPG',
                   'CPRP', 'CSD', 'CSQ',
                   'CSRS', 'LPD', 'LPQ',
                   'LPG', 'LPRP', 'LPRD',
                   'LSD', 'LSQ', 'LSRS',
                   'LSRD', 'RX', 'ZTD',
                   'ZTR', 'GB', 'YTD',
                   'YTR', 'VDID']

FUNC_DICT = {'Cp-D': 'CPD',
             'Cp-Q': 'CPQ',
             'Cp-G': 'CPG',
             'Cp-Rp': 'CPRP',
             'Cs-D': 'CSD',
             'Cs-Q': 'CSQ',
             'Cs-Rs': 'CSRS',
             'Lp-D': 'LPD',
             'Lp-Q': 'LPQ',
             'Lp-G': 'LPG',
             'Lp-Rp': 'LPRP',
             'Lp-Rdc': 'LPRD',
             'Ls-D': 'LSD',
             'Ls-Q': 'LSQ',
             'Ls-Rs': 'LSRS',
             'Ls-Rdc': 'LSRD',
             'R-X': 'RX',
             'Z-Thd': 'ZTD',
             'Z-Thr': 'ZTR',
             'G-B': 'GB',
             'Y-Thd': 'YTD',
             'Y-Thr': 'YTR',
             'Vdc-Idc': 'VDID',}

PARAMETERS_BY_FUNC = {'CPD': ['Capacitance (Parallel) [F]', 'Loss Tangent', 'Data Status'],
                      'CPQ': ['Capacitance (Parallel) [F]', 'Quality Factor', 'Data Status'],
                      'CPG': ['Capacitance (Parallel) [F]', 'Eq. Parallel Conductance [S]', 'Data Status'],
                      'CPRP': ['Capacitance (Parallel) [F]', 'Eq. Parallel Resistance [Ohm]', 'Data Status'],
                      'CSD': ['Capacitance (Series) [F]', 'Loss Tangent', 'Data Status'],
                      'CSQ': ['Capacitance (Series) [F]', 'Quality Factor', 'Data Status'],
                      'CSRS': ['Capacitance (Series) [F]', 'Eq. Series Resistance [Ohm]', 'Data Status'],
                      'LPD': ['Inductance (Parallel) [F]', 'Loss Tangent', 'Data Status'],
                      'LPQ': ['Inductance (Parallel) [F]', 'Quality Factor', 'Data Status'],
                      'LPG': ['Inductance (Parallel) [F]', 'Eq. Parallel Conductance [S]', 'Data Status'],
                      'LPRP': ['Inductance (Parallel) [F]', 'Eq. Parallel Resistance [Ohm]', 'Data Status'],
                      'LPRD': ['Inductance (Parallel) [F]', 'Direct Current Resistance [Ohm]', 'Data Status'],
                      'LSD': ['Inductance (Series) [F]', 'Loss Tangent', 'Data Status'],
                      'LSQ': ['Inductance (Series) [F]', 'Quality Factor', 'Data Status'],
                      'LSRS': ['Inductance (Series) [F]', 'Eq. Series Resistance [Ohm]', 'Data Status'],
                      'LSRD': ['Inductance (Series) [F]', 'Direct Current Resistance [Ohm]', 'Data Status'],
                      'RX': ['Resistance [Ohm]', 'Reactance [Ohm]', 'Data Status'],
                      'ZTD': ['Impedance [Ohm]', 'Theta [deg]', 'Data Status'],
                      'ZTR': ['Impedance [Ohm]', 'Theta [rad]', 'Data Status'],
                      'GB': ['Eq. Parallel Conductance [S]', 'Susceptance [S]', 'Data Status'],
                      'YTD': ['Admittance [S]', 'Theta [deg]', 'Data Status'],
                      'YTR': ['Admittance [S]', 'Theta [rad]', 'Data Status'],
                      'VDID': ['Direct Current Voltage [V]', 'Direct Current Electricity [A]', 'Data Status']}

VALID_IMP_RANGES = ['Auto',
                    '1E-1',
                    '1E+0',
                    '1E+1',
                    '1E+2',
                    '3E+2',
                    '1E+3',
                    '3E+3',
                    '1E+4',
                    '3E+4',
                    '1E+5']

TRIG_SOURCE_DICT = {'Internal': 'INT',
                    'Manual': 'HOLD',
                    'External': 'EXT',
                    'Bus': 'BUS'}

MEASURE_TIME_DICT = {'Long': 'LONG',
                     'Medium': 'MED',
                     'Short': 'SHOR'}