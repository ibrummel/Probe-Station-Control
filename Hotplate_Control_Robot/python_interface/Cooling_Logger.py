from Hotplate_Robot_Temp_Calibration import TempCal
from time import sleep

if __name__ == "__main__":
    temp = 999.9
    tempcal = TempCal(logfile="2021.05.20_Hotplate_Temp_Calibration_CoolingLog.csv", port='COM4', baud=115200)
    count = 0
    
    
    measure_interval = 10  # Seconds
    save_time = 30  # minutes
    save_count = (save_time * 60 ) / measure_interval
    
    while temp > 25.0:
        row = tempcal.get_row()
        temp = row['temp']
        
        print("Got temperature from row: {} --> Temp: {}".format(row, temp))
        sleep(measure_interval)
        
        if count > save_count:
            count = 0
            tempcal.write_data()
        