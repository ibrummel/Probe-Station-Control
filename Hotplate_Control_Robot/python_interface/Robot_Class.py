import serial


class HotplateRobot(object):
    def __init__(self, port: str, baud: int, timeout=0.05):
        super().__init__()
        self.robot = serial.Serial(port, baud, timeout=timeout)
        self.last_move = None

    def read_response(self, start_char='<', end_char='>'):
        rc = self.robot.read()
        start_char = start_char.encode('utf-8')
        end_char = end_char.encode('utf-8')
        # print("Read Character: {}".format(rc))
        if rc == start_char:
            response = b''
            while rc != end_char:
                rc = self.robot.read()
                response += rc
            return response.strip(b' ' + end_char).decode('utf-8')
        else:
            return self.read_response()

    def update_position(self, position: int, start_char='!', end_char='\r'):
        if position > 180:
            position = 180
        elif position < 0:
            position = 0
        update = start_char + "p," + str(position) + end_char
        self.robot.write(update.encode('utf-8'))

    def set_setpoint(self, stpt: float):
        pos = int(4.08339e-5*(stpt**2) - (2.8737e-1 * stpt) + 1.54425e2)

        self.update_position(pos)

    def query_param(self, query: str, start_char='?', end_char='\r'):
        query = start_char + query + end_char
        self.robot.write(query.encode('utf-8'))
        return self.read_response()

    def get_temp(self):
        temperature = self.query_param('t')
        temperature = float(temperature)

        return temperature
