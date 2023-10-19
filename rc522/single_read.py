#!/usr/bin/env python

import RPi.GPIO as GPIO
import MFRC522_single
import signal


def read(object):
    object.MFRC522_Init()

    # 인식 오류 대비 3번씩 인식
    for j in range(3):
        # Scan for cards
        (status,TagType) = object.MFRC522_Request(object.PICC_REQIDL)

        # Get the UID of the card
        (status,uid) = object.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == object.MI_OK:
            # uid 값 반환
            return f'${uid[0]}${uid[1]}${uid[2]}${uid[3]}'

    return -1


if __name__ == "__main__":
    def end_read(signal,frame):
        print("Ctrl+C captured.")
        GPIO.cleanup()


    signal.signal(signal.SIGINT, end_read)

    # Create an object of the class MFRC522
    RC522 = MFRC522_single.MFRC522(22)

    while True:
        result = read(RC522)

        if(result != -1):
            print('detected!\n\tuid :', result)