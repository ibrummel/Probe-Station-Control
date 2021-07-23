from datetime import datetime
from time import sleep
import pandas as pd
from Instrument_Interfaces.HotplateRobot import HotplateRobot

class TempCal():
    def __init__(self, logfile: str, port='COM4', baud=115200, timeout=0.5):
        super(TempCal, self).__init__()
        print("Opening port to robot...")
        self.robot = HotplateRobot(port, baud, timeout=timeout)
        self.last_move = None
        print("Building dataframe...")
        self.df = pd.DataFrame(columns=['timestamp', 'last_move', 'position', 'temp',])
        print("Setting logfile location...")
        self.logfile = logfile
        print("Logging to: {}".format(self.logfile))

        
    def get_row(self):
        row = dict(timestamp=datetime.now(),
                    last_move=self.last_move,
                    position=int(self.robot.query_param('p')),
                    temp=float(self.robot.query_param('t')))
        self.df = self.df.append(row, ignore_index=True)
        return row
    
    def write_data(self):
        self.df.to_csv(self.logfile, sep=',', header=True, index=False)
    
    def move_to_next(self):
        new_position = int(self.robot.query_param('p')) - 5
        self.last_move = datetime.now()
        self.robot.update_position(new_position)

        self.write_data()


if __name__ == "__main__":
    print("Building Temperature Calibration...")
    tempcal = TempCal(logfile="2021.05.19_Hotplate_Temp_Calibration_Log.csv", port='COM4', baud=115200)

    print("Starting Hotplate Robot Temp Calibration.\nCurrent Position:\t{}\nLogging to file:\t{}\n".format(tempcal.robot.query_param('p'), tempcal.logfile,))
    

    complete = False
    count = 0

    measure_interval = 10  # Seconds
    equil_time = 30  # minutes
    equil_count = (equil_time * 60 ) / measure_interval

    while not complete:
        print(tempcal.get_row())
        count += 1
        sleep(measure_interval) # Measure every 10 second
        
        if count == equil_count:
            if int(tempcal.robot.query_param('p')) <= 0:
                complete = True
                print("Measurement complete. Returning to hotplate off.")
                tempcal.robot.update_position(180)
            else:
                tempcal.move_to_next()
                count=0
