import numpy as np
from math import trunc


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
