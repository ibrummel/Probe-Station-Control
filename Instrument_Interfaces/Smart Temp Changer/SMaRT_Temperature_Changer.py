import argparse
import os
import sys
import json

sys.path.append(r"C:\Users\Public\Ihlefeld_Apps\Probe-Station-Control")
from time import time, sleep
from datetime import timedelta, datetime
import numpy as np
from Instrument_Interfaces.Sun_EC1X import SunEC1xChamber
from Instrument_Interfaces.HotplateRobot import HotplateRobot
from Instrument_Interfaces.Instec_MK2000B import MK2000B

parser = argparse.ArgumentParser(description="Set a temperature from SMaRT")

parser.add_argument('--file', dest='file_path', type=str,
                    help='Provide a file path for saving the temperature record data + logging.')
parser.add_argument('-i', '--instrument', '--inst', type=str, dest='ctrl_inst', default='None',
                    nargs='?', help='Choose the temperature control instrument. Valid values=[sun, hotplate, mk2000b].')
parser.add_argument('-t', '-T', '--temp', '--temperature', dest='step_temp', nargs='?', default=35, type=float,
                    help='Choose the temperature to set on the control instrument. Set to any number below 0 to run '
                         'the shutdown procedure for the selected instrument. Defaults to 35C if not provided.')
parser.add_argument('--tol', dest='temp_tol', nargs='?', default=0.5, type=float,
                    help='Provide a value for the difference between the measured temperature and the goal temperature'
                         'where statistics start being recorded. Note: Default value=0.5\'C, Ignored if using hotplate'
                         'robot for temperature control')
parser.add_argument('--stdevtol', dest='stdev_tol', nargs='?', default=0.5, type=float,
                    help='Provide maximum allowable standard deviation of temperature to be considered stable.')
parser.add_argument('--ramp', dest='ramp_time', nargs='?', default=10, type=float,
                    help='Sets the number of minutes to allow the hotplate to heat to its setpoint. Defaults to 10 min.'
                         'Ignored if not using hotplate robot to control temperature.')
parser.add_argument('--dwell', dest='dwell', nargs='?', default=10, type=float,
                    help='Sets the number of minutes to track temperature for checking stability. Defaults to 10 min.')
parser.add_argument('--stab_int', dest='stab_int', nargs='?', default=5, type=int,
                    help='Integer number of seconds to wait between taking measurements during stabilization period.')

# Create a generic temperature controller object to set as a reference to the actual object we want later. Interfaces
#  have standard calls to allow this interchangeability.
temperature_controller = None

# Read the instrument addresses defined in instrument_addresses.json file
path = r'C:/Users/Public/Ihlefeld_Apps/Probe-Station-Control/Instrument_Interfaces/instrument_addresses.json'
with open(path, 'r') as file:
    data = file.read()
instrument_addresses = json.loads(data) 
# Parse Arguments and setup temperature controller
args = parser.parse_args()
print('Args parsed as: {}'.format(args))
if args.ctrl_inst.lower() == 'sun':
    sun = SunEC1xChamber(gpib_addr=instrument_addresses[args.ctrl_inst])
    sun.set_ramprate(5)
    sun.sun.write('COFF')
    temperature_controller = sun
elif args.ctrl_inst.lower() == 'hotplate':
    print('Got hotplate as instrument')
    hotplate_robot = HotplateRobot(port=instrument_addresses[args.ctrl_inst], baud=115200)
    temperature_controller = hotplate_robot
elif args.ctrl_inst.lower() == 'mk2000b':
    mk2000b = MK2000B(instrument_addresses[args.ctrl_inst])
    temperature_controller = mk2000b
else:
    raise ValueError('Invalid instrument supplied')


if not os.path.exists(args.file_path):
    with open(args.file_path, 'w') as logfile:
        header_modification = 'Ramp Time (min)' if temperature_controller.PID_enabled else 'Ramp Rate (C/min)'
        logfile.write('Timestamp,Setpoint Temp (C),Average Temp (C),Stdev Temp (C),Stdev Tolerance,'
                      'Control Instrument,{},Dwell(min),Stabilization Interval(sec)\n').format(header_modification)


def log_to_file(log_str: str, file_path=args.file_path + '_log'):
    with open(file_path, 'a') as logfile:
        tstamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tstamped_str = '{timestamp},{log_str}\n'.format(timestamp=tstamp, log_str=log_str)
        logfile.write(tstamped_str)
        print(tstamped_str.strip(), end='\r')


def blocking_func():
    # DONE: Behavior based on selected temperature control device.
    if args.ctrl_inst == "None":
        pass
    else:
        # Define variables to hold logged temperatures
        chamber_temp = []

        # Send the command to change the temperature
        # DONE: 2 Change all branches of this type to be less manual if possible.
        temperature_controller.set_setpoint(args.step_temp)
        log_to_file("Waiting for {} to reach {}...".format(temperature_controller.instrument_name_string,
                                                           args.step_temp))
        print('')

        if temperature_controller.PID_enabled:
            # Get the current temperature and loop until setpoint is achieved
            check_temp = float(temperature_controller.get_temp())
            temperature_controller.set_ramprate(args.ramp_time)
            if args.step_temp > check_temp:
                while check_temp < args.step_temp - args.temp_tol:
                    check_temp = float(temperature_controller.get_temp())
                    print('Current Temperature: {}'.format(check_temp), end='\r')
                    sleep(1)
            elif args.step_temp < check_temp:
                while check_temp > args.step_temp + args.temp_tol:
                    check_temp = float(temperature_controller.get_temp())
                    print('Current Temperature: {}'.format(check_temp), end='\r')
                    sleep(1)
        elif not temperature_controller.PID_enabled:
            # Use a running average of last 60 seconds to determine if heating has finished + temperature
            #  is stabilized.
            count = 0
            while True:
                chamber_temp = chamber_temp[-60:]
                chamber_temp.append(float(hotplate_robot.get_temp()))
                print('Current Temperature: {}'.format(chamber_temp[-1]), end='\r')
                count += 1
                sleep(1)
                if count >= int(args.ramp_time * 60):
                    print('')
                    log_to_file("Non-PID ramp time complete. "
                                "Temperature standard deviation = {}".format(np.std(chamber_temp)))
                    if np.std(chamber_temp) < args.stdev_tol:
                        chamber_temp = []
                        break
            print('')

        # After reaching setpoint, check stability
        # Blocking loop for temperature equilibration
        count = 0
        start_time = time()
        for i in range(0, int(args.dwell * 60)):
            if count % args.stab_int == 0:
                curr_temp = temperature_controller.get_temp()
                chamber_temp.append(curr_temp)
                sleep(0.05)
            count += 1
            time_left = str(timedelta(seconds=int(args.dwell * 60) - i))
            print("Checking stability at {temp}. Current Temperature: {curr_temp}, Time Remaining: {time}".format(
                temp=args.step_temp, curr_temp=curr_temp, time=time_left), end='\r')
            sleep(0.956)
        print('')

        log_to_file(
            'Temperature stability check was scheduled for {} s, and took {} s.'.format(args.dwell * 60,
                                                                                        time() - start_time))
        print('')

        # Calculate temperature statistics
        chamber_avg = np.mean(chamber_temp)
        chamber_stdev = np.std(chamber_temp)
        print(chamber_temp, chamber_avg, chamber_stdev)
        # Check that statistics are within user specification. Re-run equilibration if so.
        in_spec = True
        if temperature_controller.PID_enabled and abs(chamber_avg - args.step_temp) > args.temp_tol:
            log_to_file('Temperature too far from setpoint ({delta} vs {deltol}) outside of tolerance.'.format(
                delta=abs(chamber_avg - args.step_temp), deltol=args.temp_tol))
            in_spec = False
        if chamber_stdev > args.stdev_tol:
            log_to_file('Temperature unstable. Standard deviation ({stdev} vs {stdevtol}) outside of tolerance.'.format(
                stdev=chamber_stdev, stdevtol=args.stdev_tol))
            in_spec = False

        if not in_spec:
            sleep(2)
            log_to_file('Attempting to stabilize temperature at stpt={} again...'.args.step_temp)
            return blocking_func()
    return chamber_avg, chamber_stdev


if temperature_controller is None:
    input('No valid temperature controller. No one should ever see this message printed. Press any key to exit')
elif args.step_temp < 0:
    log_to_file(temperature_controller.shutdown())
else:
    avg, stdev = blocking_func()
    data_str = '{stpt},{avg},{stdev},{stdev_tol},{ctrl_inst},{ramp},{dwell},{stab_int}'.format(stpt=args.step_temp,
                                                                                               avg=avg,
                                                                                               stdev=stdev,
                                                                                               stdev_tol=args.stdev_tol,
                                                                                               ctrl_inst=args.ctrl_inst,
                                                                                               ramp=args.ramp_time,
                                                                                               dwell=args.dwell,
                                                                                               stab_int=args.stab_int)
    log_to_file(data_str)
    log_to_file(data_str, args.file_path)
    sleep(1)
