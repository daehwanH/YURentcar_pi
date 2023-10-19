#!/usr/bin/env python

import RPi.GPIO as GPIO
import MFRC522_multi
import signal


# MFRC522 객체와 활성화 할 센서의 rst 핀 번호의 배열을 넘겨줌
def read(object, active_num_arr):
    # 결과 반환할 딕셔너리, 각 센서별 값 -1로 초기화
    result = dict.fromkeys(active_num_arr, -1)

    # 활성화 할 센서들 순회
    for i in range(active_num_arr):
        object.MFRC522_Init(active_num_arr[i])

        # 인식 오류 대비 센서당 3번씩 인식
        for j in range(3):
            # Scan for cards
            (status,TagType) = object.MFRC522_Request(RC522.PICC_REQIDL)

            # Get the UID of the card
            (status,uid) = object.MFRC522_Anticoll()

            # If we have the UID, continue
            if status == object.MI_OK:
                # 딕셔너리에 uid 값 저장
                result[active_num_arr[i]] = f'${uid[0]}${uid[1]}${uid[2]}${uid[3]}'
                break

    return result


if __name__ == "__main__":
    def end_read(signal,frame):
        print("Ctrl+C captured.")
        GPIO.cleanup()


    sensor_name = ['센서0', '센서1', '센서2']

    # Hook the SIGINT
    signal.signal(signal.SIGINT, end_read)

    # Create an object of the class MFRC522
    RC522 = MFRC522_multi.MFRC522([16, 18, 22])

    while True:
        result = read(RC522, [16, 18, 22])

        # result의 결과값에서 -1이 아닌 값만 처리
        for i in result:
            print(f'pin {i} : {result[i]}' if result[i] != -1 else f'pin {i} : not detected')