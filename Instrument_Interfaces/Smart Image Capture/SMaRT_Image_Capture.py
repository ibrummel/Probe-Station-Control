import argparse
import os
import cv2
import subprocess
from time import sleep

try:
    parser = argparse.ArgumentParser(description="Take electrode images using instec probe station camera.")

    parser.add_argument('--dir', dest='file_path', nargs='?', default="Electrode_Images", type=str,
                        help='Provide a file path for saving the temperature record data + logging.')
    parser.add_argument('--file', dest='file_base', type=str,
                        help='Provide a base string for image naming.')
    parser.add_argument('-t', '-T', '--temp', '--temperature', dest='step_temp', nargs='?', default=35, type=float,
                        help='Choose the temperature to set on the control instrument. Set to any number below 0 to run '
                             'the shutdown procedure for the selected instrument. Defaults to 35C if not provided.')

    # Start camera then kill the app to force auto whitebalance and contrast to run
    subprocess.run("start microsoft.windows.camera:", shell=True)
    sleep(5)
    subprocess.run("Taskkill /IM WindowsCamera.exe /F", shell=True)

    # Parse Arguments
    args = parser.parse_args()
    print('Args parsed as: {}'.format(args))

    # Generate Directory for images if not present
    if not os.path.exists(args.file_path):
        os.mkdir(args.file_path)

    webcam = cv2.VideoCapture(0)
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    check, frame = webcam.read()
    try:
        index = len(os.listdir(args.file_path))
        if check:
            cv2.imwrite(filename=os.path.join(args.file_path, "{}_{}_{}.png".format(index, args.step_temp, args.file_base)), img=frame)
        else:
            with open(os.path.join(args.file_path, "{}_{}_{}_error.txt".format(index, args.step_temp, args.file_base)), 'w') as file:
                file.write("Error on getting image. No exception thrown")
    except Exception as err:
        with open(os.path.join(args.file_path, "{}_{}_{}_error.txt".format(index, args.step_temp, args.file_base)), 'w') as file:
            file.write("Error on getting image. Following exception thrown:\n")
            file.write(repr(err))
    finally:
        webcam.release()
        cv2.destroyAllWindows()
except Exception as err:
    print("Script hit an error:", err)
    input("Press any key to continue...")