import pyvisa
from time import time, sleep


class MK2000B(object):
    def __init__(self, inst_addr: str, baud=9600, timeout=50, dead_time=50):
        super(MK2000B, self).__init__()
        self.controller = pyvisa.ResourceManager().open_resource(inst_addr, baud_rate=baud, timeout=timeout,
                                                                 write_termination='\r\n', read_termination='\r\n')

        self.last_RTIN_update = 0
        self.dead_time = float(dead_time/1000)
        self.RTIN = {}
        self.update_RTIN()
        self.ramp = self.get_ramp_rate()
        
    # Don't have this one figured out yet
    # def set_rate(self):
        # self.controller.write('Temp:Rate')

    def set_setpoint(self, stpt: float, rate=5):
        self.controller.write('Temp:RAMP {},{}'.format(stpt, rate))

    def stop(self):
        self.controller.write('Temp:STOP')

    def update_RTIN(self):
        tnow = time()
        if tnow-self.last_RTIN_update >= self.dead_time:
            RTIN_parts = self.controller.query('Temp:RTIN?').split(':')

            RTIN = {'model?': RTIN_parts[0],
                    'isnt_num?': RTIN_parts[1],
                    'temp': float(RTIN_parts[2]),
                    'MV?': RTIN_parts[3],
                    'stpt': float(RTIN_parts[4]),
                    'c_stpt': float(RTIN_parts[5]),
                    'ramp': float(RTIN_parts[6]),
                    'pwr': float(RTIN_parts[7]),
                    'mode': int(RTIN_parts[8]),  #NOTE: Stop=0, Hold=1, Ramp=2, Const Power=5,
                    'tuple?': RTIN_parts[9],
                    '?': RTIN_parts[10],
                    }
            self.last_RTIN_update = tnow
            self.RTIN = RTIN

    def get_temp(self):
        self.update_RTIN()
        return self.RTIN['temp']

    def get_current_stpt(self):
        self.update_RTIN()
        return self.RTIN['c_stpt']

    def get_temp_stpt(self):
        self.update_RTIN()
        return self.RTIN['stpt']

    def get_power(self):
        self.update_RTIN()
        return self.RTIN['pwr']

    def get_ramp_rate(self):
        self.update_RTIN()
        return self.RTIN['ramp']
