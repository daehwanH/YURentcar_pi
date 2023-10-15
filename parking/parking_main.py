'''
주차장 라즈베리파이 제어용 메인 파일
서버 통신, 센서 인식, 상태에 따른 센서 인식 여부 제어
초음파 센서
1. 기본적으로 10초마다 한번씩 거리를 체크한다. (상태 0)
2. 일정 거리 미만으로 측정될 경우 1초마다 거리를 체크한다. (상태 1로)
    2.1. 다시 해당거리 이상으로 체크된 경우 1로 돌아간다. (상태 0로)
    2.2. 오차범위 안쪽으로 7번의 측정거리가 같은 경우 주차로 판단한다. (상태 2로)
        2.2.1. 해당 경우 백엔드에 해당 자리에 주차가 되었음을 알린다.
        2.2.2. 해당 자리의 RFID 센서를 활성화한다. (상태 3로)
        2.2.3. RFID 태그가 정상적으로 확인 된 경우 상태 4로 바꾼다.

상태별 led
    0 = 소등
    1 = 흰색 점멸
    2 = 흰색 점등
    3 = 노란색 점등
    31(성공) = 녹색 점멸
    30(실패) = 붉은색 점멸
    4 = 파란색 점등

# 현재 RFID가 작동하지 않아 30, 31은 없는 상태
'''


import RPi.GPIO as GPIO
import time
import datetime
import multiprocessing
from multiprocessing import shared_memory
from queue import Queue
import threading
import requests
import json
from hc_sr04 import *
from parking.rc522 import *


#seat_length = 500      # 주차 자리 길이, 1초마다 체크하는 기준
seat_length = 20        # 프로토타입 주차 자리 길이
sensor_num = 3          # 주차장 자리(센서)의 수

url = ''                # 추후 백엔드 연결용 주소 저장 변수

# 상태값 저장 리스트
status = shared_memory.ShareableList([0 for i in range(sensor_num)])

manager = multiprocessing.Manager()

# 초음파센서 클래스 객체 리스트
us = manager.list()
us = ([hc_sr04(13, 16), hc_sr04(19, 20), hc_sr04(26, 21)])

# RFID 백엔드 체크 후 응답을 저장할 리스트
response = manager.list()

# 백엔드 연결 후 통신 실패시 로그 기록용 리스트
log = manager.list()

# led 제어 프로세스용 함수
# 1초에 한주기, 점멸의 경우 0.5초 켜지고 0.5초 꺼지게 구현
def led():
    last = [0 for i in range(sensor_num)]   # 이전 상태 저장
    led = [(14, 15, 18), (17, 27, 22), (0, 5, 6)]
    n = [0 for i in range(sensor_num)]      # 반복 횟수 저장

    # GPIO 모드 설정, led 핀 output으로 설정
    GPIO.setmode(GPIO.BCM)
    for i in led:
        for j in i:
            GPIO.setup(j, GPIO.OUT)

    def on(led_num, r, g, b):   # r, g, b 색상별로 on, off 하는 함수
        GPIO.output(led_num[0], r)
        GPIO.output(led_num[1], g)
        GPIO.output(led_num[2], b)

    def off(led_num):           # led를 끄는 함수
        GPIO.output(led_num[0], 0)
        GPIO.output(led_num[1], 0)
        GPIO.output(led_num[2], 0)

    while True:
        # 각 자리를 순회하면서 이전 상태와 현재 상태 비교
        for i in range(sensor_num):
            if status[i] != last[i]:    # 상태가 다를경우 반복 횟수 초기화
                n[i] = 0
            last[i] = status[i]

        # 상태별 색, 깜빡임 설정
        for i in range(sensor_num):
            if last[i] == 0:
                off(led[i])
            elif last[i] == 1:
                on(led[i], 1, 1, 1)
            elif last[i] == 2:
                on(led[i], 1, 1, 1)
            elif last[i] == 3:
                on(led[i], 1, 1, 0)
            elif last[i] == 30:
                on(led[i], 1, 0, 0)
            elif last[i] == 31:
                on(led[i], 0, 1, 0)
            elif last[i] == 4:
                on(led[i], 0, 0, 1)

        time.sleep(0.5)

        for i in range(sensor_num):
            if last[i] == 1:
                off(led[i])
            elif last[i] == 30:
                off(led[i])
                n[i] += 1
                if n[i] == 3:
                    n[i] = 0
                    status[i] = 3
            elif last[i] == 31:
                off(led[i])
                n[i] += 1
                if n[i] == 3:
                    n[i] = 0
                    status[i] = 4

        time.sleep(0.5)


def send(type, content):
    t = 3 # 통신 시도 횟수
    dic = {
        'title' : '',
        'site' : '',
        'time' : '',
    }

    if type == 10:
        for i in range(t):
            # 차량 주차 확인
            print("차량 주차 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['title'] = 'parking'
            dic['site'] = content[0]
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 자리 번호를 백엔드로 전송
            r = requests.put(url, data=data)
            if r.status_code != 200:
                log.append(data)
        return
    elif type == 11:
        for i in range(t):
            # 차량 출차 확인
            print("차량 출차 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['title'] = 'exit'
            dic['site'] = content[0]
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 자리 번호를 백엔드로 전송
            r = requests.put(url, data=data)
            if r.status_code != 200:
                log.append(data)
        return
    elif type == 20:
        for i in range(t):
            # 차량 주차 후 rfid 체크
            print("RFID 인식 : {}번 자리 | ID : {} | 시간 : {}".format(content[0], content[1], content[2]))
            dic['title'] = 'rf_check'
            dic['site'] = content[0]
            dic['id'] = content[1]
            dic['time'] = content[2]
            data = json.dumps(dic)
            # 읽힌 태그 id를 백엔드로 전송
            r = requests.put(url, data=data)
            if r.status_code == 200:
                response.append((content[0], r.status_code))
                return
            else:
                log.append(data)
        return
    elif type == 21:
        for i in range(t):
            # 차량 주차 후 일정시간동안 rfid 미체크
            print("RFID 미인식 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['title'] = 'rf_uncheck'
            dic['site'] = content[0]
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 체크가 안된 자리 번호를 백엔드로 전송
            r = requests.put(url, data=data)
            if r.status_code != 200:
                log.append(data)
        return
    elif type == 30:
        # 추가할때 복붙용
        return


def detect(num):
    d_array = []
    n = 0

    while True:
        time.sleep(1)
        d = us[num].run()
        print("탐지({}) : 상태 {}, 측정거리 {:.2f}".format(num, status[num], d))
        if d > seat_length:
            status[num] = 0
            return
        elif d > (seat_length / 2):
            n = 0
            d_array.clear()
            continue
        else:
            n += 1
            if len(d_array) == 10:
                del d_array[0]
            d_array.append(d)
            if max(d_array) - min(d_array) > 2:
                n = 0
            if n == 7:
                status[num] = 2
                # t = datetime.datetime.now()
                # s_t = threading.Thread(target=send, args=(10, (num, t)))
                # s_t.start()
                return


# 500cm 기준으로 10초마다 체크
# 500cm 안쪽이 감지된 경우 1초마다 체크
# 프로토타입의 경우 20cm 기준, 기본 상태에서 5초마다 체크
def ultrasonic():
    distance = [None for i in range(sensor_num)]
    n = [0 for i in range(sensor_num)]

    while True:
        for i in range(sensor_num):
            if status[i] == 0:
                distance[i] = us[i].run()
                print("기본({}) : 상태 {}, 측정거리 {:.2f}".format(i, status[i], distance[i]))
                if distance[i] < seat_length:
                    status[i] = 1
                    # detect를 스레드로 실행
                    detect_t = threading.Thread(target=detect, args=(i,))
                    detect_t.start()
            elif status[i] == 2 or status[i] == 3 or status[i] == 30 or status[i] == 31 or status[i] == 4:
                distance[i] = us[i].run()
                print("기본({}) : 상태 {}, 측정거리 {:.2f}".format(i, status[i], distance[i]))
                if distance[i] > seat_length:
                    n[i] += 1
                    if n[i] == 3:
                        status[i] = 0
                        n[i] = 0
                        # t = datetime.datetime.now()
                        # s_t = threading.Thread(target=send, args=(11, (i, t)))
                        # s_t.start()
                else:
                    n[i] = 0

        time.sleep(10)


# RFID 리더가 다 작동하지 않아 임시로 만든 테스트용 코드
# 프로그램 시작시 1, 0값의 리스트를 받아 큐에 저장,
# 해당 큐에서 뽑아낸 값에 따라 RFID 인식 성공과 실패로 동작하게 설정
def rfid():
    while True:
        for i in range(sensor_num):
            if status[i] == 2:
                time.sleep(3) # rfid 인식 시간용
                status[i] = 3
                a = rfid_result.get()
                if a == 1:
                    status[i] = 4
                elif a == 0:
                    status[i] = 2
        time.sleep(1)


# rc522가 다 죽어버린 관계로 주석처리
'''
def rfid():
    nfc = NFC()
    nfc.addBoard('0', 23)
    q = Queue()

    def read(nfc, rfid_num):
        rfid_id = nfc.read(str(rfid_num))
        q.put((rfid_num, rfid_id))

    def timer(nfc, rfid_num):
        r = threading.Thread(target=read, args=(nfc, rfid_num,), daemon=True)
        r.start()
        time.sleep(10)
        if q.empty() == False:
            info1, info2 = q.get()
            # t = datetime.datetime.now()
            # r_t = threading.Thread(target=send, args=(20, (info1, info2, t)))
            # r_t.start()

    while True:
        for i in range(sensor_num):
            print("rfid {} : 상태 {}".format(i, status[i]))
            if status[i] == 2:
                status[i] = 3
                t = threading.Thread(target=timer, args=(nfc, 0,))
                t.start()
        while len(response) != 0:
            index, check = response.pop(0)
            if check == 200:
                # 디비에 있는 rfid id
                # 초록색 led on
                if status[index] == 3:
                    status[index] = 31
            else:
                # 디비에 없는 rfid id
                # 빨간색 led on
                if status[index] == 3:
                    status[index] = 30
        time.sleep(1)
'''


if __name__ == '__main__':
    try:
        rfid_result = Queue()
        temp = []
        temp = input("rfid 결과 배열(공백으로 구분) >> ").split(' ')
        for i in temp:
            rfid_result.put(int(i))

        p_led = multiprocessing.Process(target=led)
        p_us = multiprocessing.Process(target=ultrasonic)
        p_rfid = multiprocessing.Process(target=rfid)

        p_led.start()
        p_us.start()
        p_rfid.start()

        p_led.join()
        p_us.join()
        p_rfid.join()

    except KeyboardInterrupt:
        status.shm.close()
        status.shm.unlink()
        GPIO.cleanup()
