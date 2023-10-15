import RPi.GPIO as GPIO
import time


class solenoid():
    def __init__(self, box, led):
        self.box = box
        self.led = led
        GPIO.setmode(GPIO.BCM)
        for i in box:
            GPIO.setup(i, GPIO.OUT)
            GPIO.output(i, 1)
        for i in led:
            GPIO.setup(i, GPIO.OUT)
            GPIO.output(i, 0)


    def box_open(self, num):
        GPIO.output(self.led[num], 1)
        time.sleep(1)
        GPIO.output(self.box[num], 0)
        time.sleep(3)
        GPIO.output(self.box[num], 1)
        GPIO.output(self.led[num], 0)


if __name__ == "__main__":
    try:
        box = [14, 15, 18]
        led = [2, 3, 4]
        sol = solenoid(box, led)
        sol.box_open(0)
        sol.box_open(1)
        sol.box_open(2)

    except KeyboardInterrupt:
        GPIO.cleanup()
