from Instrument_Interfacees.Sun_EC1X import SunEC1xChamber
import pandas as pd
from time import sleep, time
from datetime import timedelta, datetime
from statistics import stdev, mean, StatisticsError


def temp_step(step_temp: float, log_file: str, ramp=5.0, dwell=30, stab_int=10, temp_tol=0.5, stdev_tol=0.5):
    sun = SunEC1xChamber(parent=None, gpib_addr='GPIB0::6::INSTR')

    df = pd.DataFrame(columns=['timestamp', 'user_t', 'chamber_t'])
    row = {}

    # Send the command to change the temperature
    sun.set_ramprate(ramp)
    sun.set_setpoint(step_temp)

    # Get the current temperature and loop until setpoint is achieved
    check_temp = float(sun.get_temp())
    if step_temp > check_temp:
        while check_temp < step_temp - temp_tol:
            check_temp = float(sun.get_temp())
            print("Current Temp: {:.2f}".format(check_temp), end='\r')
            sleep(1)
    elif step_temp < check_temp:
        while check_temp > step_temp + temp_tol:
            check_temp = float(sun.get_temp())
            print("Current Temp: {:.2f}".format(check_temp), end='\r')
            sleep(1)
    # Move console output to new line
    print('\n')

    # Blocking loop for temperature equilibration
    count = 0
    start_time = time()
    for i in range(0, int(dwell * 60)):
        if count % stab_int == 0:
            row['timestamp'] = datetime.now()
            row['user_t'] = sun.get_user_temp()
            sleep(0.05)
            row['chamber_t'] = sun.get_temp()
            df = df.append(row, ignore_index=True)
        count += 1
        time_left = str(timedelta(seconds=int(dwell * 60) - i))
        print("Checking stability at {temp}. Time Remaining: {time}  ".format(temp=step_temp, time=time_left), end='\r')
        sleep(1)

    # Move console output to new line
    print('\n')

    print('Temperature stability check was scheduled for {} s, and took {} s.'.format(dwell * 60,
                                                                                      time() - start_time))
    try:
        user_avg = mean(df.user_t)
        user_stdev = stdev(df.user_t, user_avg)
        chamber_avg = mean(df.chamber_t)
        chamber_stdev = stdev(df.chamber_t, chamber_avg)
    except StatisticsError:
        print('Error on performing statistics calculations.')
        user_avg = 99999
        user_stdev = 99999
        chamber_avg = 99999
        chamber_stdev = 99999
        z_stdev = 99999

    if abs(chamber_avg - step_temp) > temp_tol or chamber_stdev > stdev_tol:
        print('Temperature ({delta} vs {deltol}) or standard deviation ({stdev} vs {stdevtol}) '
              'outside of tolerance. Restarting equilibration step...'.format(delta=abs(chamber_avg - step_temp),
                                                                              deltol=temp_tol,
                                                                              stdev=chamber_stdev, stdevtol=stdev_tol))
        sleep(2)
        return temp_step(step_temp=step_temp, log_file=log_file, ramp=ramp, dwell=dwell, stab_int=stab_int,
                         temp_tol=temp_tol, stdev_tol=stdev_tol)

    # if equilibrium is good, write temp data to a file
    df.to_csv(log_file, sep=',',)
