import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT) ## GPIO 17 ouput
#GPIO.setup(27, GPIO.OUT) ## GPIO 27 output

def dooropen():
    GPIO.output(17, True)
    time.sleep(10)
    GPIO.output(17, False)
    GPIO.cleanup()
    return 0

if __name__ == "__main__":
    print("door opened!")
    dooropen()