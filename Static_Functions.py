import numpy as np
from math import trunc, floor, log10


def generate_log_steps(start, stop, num_steps):
    step = 10 ** ((np.log10(stop)-np.log10(start)) / (num_steps-1))
    freq_steps = [start * (step ** i) for i in range(0, num_steps-1)]
    freq_steps.append(stop)

    # Truncate frequencies to 2 decimal places. Probably dont even have that resolution with the lcr...
    freq_steps = [truncate_to(x, 2) for x in freq_steps]

    return freq_steps


def truncate_to(number, decimals=0):
    # Deprecated with external triggering, everything should be calculated on pulse counts now and times should be
    # rounded for display purposes
    if decimals < 0:
        raise ValueError('Cannot truncate to negative decimals ({})'.format(decimals))
    elif decimals == 0:
        return trunc(number)
    else:
        factor = float(10 ** decimals)
        return trunc(number * factor) / factor


def to_sigfigs(num, sig=2):
    return round(num, sig-int(floor(log10(abs(num))))-1)


def si_prefix(num: float, unit: str, sig=2):
    _prefix = {-18: {'mult': 10 ** 18, 'prefix': 'a'},
               -17: {'mult': 10 ** 18, 'prefix': 'a'},
               -16: {'mult': 10 ** 18, 'prefix': 'a'},
               -15: {'mult': 10 ** 15, 'prefix': 'f'},
               -14: {'mult': 10 ** 15, 'prefix': 'f'},
               -13: {'mult': 10 ** 15, 'prefix': 'f'},
               -12: {'mult': 10 ** 12, 'prefix': 'p'},
               -11: {'mult': 10 ** 12, 'prefix': 'p'},
               -10: {'mult': 10 ** 12, 'prefix': 'p'},
               -9: {'mult': 10 ** 9, 'prefix': 'n'},
               -8: {'mult': 10 ** 9, 'prefix': 'n'},
               -7: {'mult': 10 ** 9, 'prefix': 'n'},
               -6: {'mult': 10 ** 6, 'prefix': 'u'},
               -5: {'mult': 10 ** 6, 'prefix': 'u'},
               -4: {'mult': 10 ** 6, 'prefix': 'u'},
               -3: {'mult': 10 ** 3, 'prefix': 'm'},
               -2: {'mult': 10 ** 2, 'prefix': 'c'},
               -1: {'mult': 10 ** 1, 'prefix': 'd'},
               0: {'mult': 1, 'prefix': ''},
               # 1: {'mult': 10 ** -1, 'prefix': 'da'},
               1: {'mult': 1, 'prefix': ''},
               # 2: {'mult': 10 ** -3, 'prefix': 'k'},
               2: {'mult': 1, 'prefix': ''},
               3: {'mult': 10 ** -3, 'prefix': 'k'},
               4: {'mult': 10 ** -3, 'prefix': 'k'},
               5: {'mult': 10 ** -3, 'prefix': 'k'},
               6: {'mult': 10 ** -6, 'prefix': 'M'},
               7: {'mult': 10 ** -6, 'prefix': 'M'},
               8: {'mult': 10 ** -6, 'prefix': 'M'},
               9: {'mult': 10 ** -9, 'prefix': 'G'},
               10: {'mult': 10 ** -9, 'prefix': 'G'},
               11: {'mult': 10 ** -9, 'prefix': 'G'},
               12: {'mult': 10 ** -12, 'prefix': 'T'},
               13: {'mult': 10 ** -12, 'prefix': 'T'},
               14: {'mult': 10 ** -12, 'prefix': 'T'},
               15: {'mult': 10 ** -15, 'prefix': 'P'},
               16: {'mult': 10 ** -15, 'prefix': 'P'},
               17: {'mult': 10 ** -15, 'prefix': 'P'},
               18: {'mult': 10 ** -18, 'prefix': 'E'},
               }

    num = to_sigfigs(num, sig)
    order = int(log10(abs(num)))

    mult, prefix = _prefix[order]['mult'], _prefix[order]['prefix']
    num_str = str(num * mult)
    # Add zeroes to match sigfigs
    while len(num_str) < sig + 1:
        num_str += '0'
    dec_pos = num_str.find('.')
    if sig == dec_pos:
        mod = 0
    elif sig == 1:
        mod = 2
    else:
        mod = 1

    return num_str[0:(sig+mod)] + ' ' + prefix + unit