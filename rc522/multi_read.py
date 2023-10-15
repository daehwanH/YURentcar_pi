#!/usr/bin/env python

import RPi.GPIO as GPIO
import MFRC522_multi
import signal

def end_read(signal,frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    continue_reading = False
    GPIO.cleanup()

def read(sensor_num):
    RC522.MFRC522_Init(sensor_num)

    for i in range(3):
        print("try read")
        # Scan for cards
        (status,TagType) = RC522.MFRC522_Request(RC522.PICC_REQIDL)

        # Get the UID of the card
        (status,uid) = RC522.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == RC522.MI_OK:
            # Print UID
            print("Card read UID: %s,%s,%s,%s" % (uid[0], uid[1], uid[2], uid[3]))
            return uid

    return -1


if __name__ == "__main__":
    # Hook the SIGINT
    signal.signal(signal.SIGINT, end_read)

    # Create an object of the class MFRC522
    RC522 = MFRC522_multi.MFRC522([16, 18, 22])

    while True:
        read_sensor_num = input("RFID reader select (16, 18, 22) >> ")
        RC522.MFRC522_Init(read_sensor_num)
        read(read_sensor_num)