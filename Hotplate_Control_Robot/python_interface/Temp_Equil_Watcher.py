from typing import final
from Hotplate_Robot_Temp_Calibration import TempCal
import sys
from time import sleep

def watch_equil(log_file: str, port='COM4', baud=115200, measure_interval=10, save_time=20):
    try:
        logger = TempCal(log_file, port=port, baud=baud)
        save_count = (save_time * 60) / measure_interval
        count = 0

        while count <= save_count:
            row = logger.get_row()

            print(row)
            count += 1
            sleep(measure_interval)
    finally:
        logger.write_data()
        del logger

if __name__ == '__main__':
    temp_log_file = sys.argv[1]
    measure_interval = int(sys.argv[2])  # Seconds
    save_time = int(sys.argv[3])  # minutes
    
    watch_equil(temp_log_file, port='COM4', baud=115200, measure_interval=measure_interval, save_time=save_time)
