'''
hc_sr04(trig, echo) 형태로 객체 생성
trig, echo 핀 번호는 GPIO 번호로 설정 (GPIO.BCM 모드 사용)
만든 객체에 run() 함수를 실행하면 0.5초 후 거리를 측정하여 cm단위로 반환
'''


import RPi.GPIO as GPIO
import time
import sys


class hc_sr04():
    def __init__(self, trig, echo):
        if ((0 <= trig <= 27) and (0 <= echo <= 27)) == False:
            print("error!!! trig or echo pin number is abnormal!")
            sys.exit("pin number error")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)

        self.trig = trig
        self.echo = echo

        GPIO.output(self.trig, False)


# 0.5s wait, 10us trig on, echo time check, time to distance transformation
    def run(self):
        GPIO.output(self.trig, False)
        time.sleep(0.5)
        GPIO.output(self.trig, True)
        time.sleep(0.00001)
        GPIO.output(self.trig, False)

        while GPIO.input(self.echo)==0:
            start = time.time()

        while GPIO.input(self.echo)==1:
            stop = time.time()

        elapsed_time = stop - start
        distance = elapsed_time * 17150

        return distance


# test program
if __name__ == "__main__":
    try:
        us = [None for i in range(3)]
        us[0] = hc_sr04(13, 16)
        us[1] = hc_sr04(19, 20)
        us[2] = hc_sr04(26, 21)

        while True:
            i = int(input('번호 입력 (0~3)>> '))
            distance = us[i].run()
            print('hc_sr04 test\nDistance: {:.2f}cm'.format(distance))

    except KeyboardInterrupt:
        GPIO.cleanup()

    GPIO.cleanup()
