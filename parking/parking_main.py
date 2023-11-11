#!/usr/bin/python
# -*- coding: utf-8 -*-
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
'''


import RPi.GPIO as GPIO

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

import time
import multiprocessing
from multiprocessing import shared_memory
import threading
import requests
import json
from hc_sr04 import *
import MFRC522_multi
import multi_read


class Item(BaseModel):
    ID: list[int]

app = FastAPI()

@app.post("/change-id/")
async def changeID(item: Item):
    parkingSpotID = item.ID
    print(parkingSpotID)
    return True



#SEAT_LENGTH = 500       # 주차 자리 길이, 1초마다 체크하는 기준
SEAT_LENGTH = 20        # 프로토타입 주차 자리 길이
SENSOR_NUM = 3          # 주차장 자리(센서)의 수
#TIME_LIMIT = 60         # RFID 리더기 인식 제한 시간
TIME_LIMIT = 7          # 프로토타입 RFID 리더기 인식 제한 시간


url = ''                # 추후 백엔드 연결용 주소 저장 변수

# 상태값 저장 리스트
status = shared_memory.ShareableList([0 for i in range(SENSOR_NUM)])

manager = multiprocessing.Manager()

# 센서 번호와 DB 자리 id 변환용 배열
parkingSpotID = [1, 2, 3]

# rfid 센서 rst 핀 목록 배열 (BOARD)
rfid = [23, 24, 25]

# 초음파센서 클래스 객체 리스트 (BCM)
us = manager.list()
us = ([hc_sr04(13, 16), hc_sr04(19, 20), hc_sr04(26, 21)])

# 백엔드 연결 후 통신 실패시 로그 기록용 리스트
log = manager.list()

# led 제어 프로세스용 함수
# 1초에 한주기, 점멸의 경우 0.5초 켜지고 0.5초 꺼지게 구현
def led():
    last = [0 for i in range(SENSOR_NUM)]   # 이전 상태 저장
    led = [(14, 15, 18), (17, 27, 22), (0, 5, 6)]
    n = [0 for i in range(SENSOR_NUM)]      # 반복 횟수 저장

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
        for i in range(SENSOR_NUM):
            if status[i] != last[i]:    # 상태가 다를경우 반복 횟수 초기화
                n[i] = 0
            last[i] = status[i]

        # 상태별 색, 깜빡임 설정
        for i in range(SENSOR_NUM):
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

        for i in range(SENSOR_NUM):
            if last[i] == 1:
                off(led[i])
            elif last[i] == 2:
                n[i] += 1
                if n[i] == 3:
                    n[i] = 0
                    status[i] = 3
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
    dic = {}

    if type == 10:
        for i in range(t):
            # 차량 주차 확인
            print("차량 주차 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['type'] = True
            dic['site'] = content[0]
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 자리 번호를 백엔드로 전송
            r = requests.post(url, data=data)
            if r.status_code == 200:
                return True
            else:
                log.append(data)
        return False
    elif type == 11:
        for i in range(t):
            # 차량 출차 확인
            print("차량 출차 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['type'] = False
            dic['site'] = content[0]
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 자리 번호를 백엔드로 전송
            r = requests.post(url, data=data)
            if r.status_code == 200:
                return True
            else:
                log.append(data)
        return False
    elif type == 20:
        for i in range(t):
            # 차량 주차 후 rfid 체크
            print("RFID 인식 : {}번 자리 | ID : {} | 시간 : {}".format(content[0], content[1], content[2]))
            dic['type'] = True
            dic['site'] = content[0]
            dic['id'] = content[1]
            dic['time'] = content[2]
            data = json.dumps(dic)
            # 읽힌 태그 id를 백엔드로 전송
            r = requests.post(url+'rfid/', data=data)
            if r.status_code == 200:
                status[content[0]] = 31
                return True
            else:
                log.append(data)
            
        return False
    elif type == 21:
        for i in range(t):
            # 차량 주차 후 일정시간동안 rfid 미체크
            print("RFID 미인식 : {}번 자리 | 시간 : {}".format(content[0], content[1]))
            dic['type'] = False
            dic['site'] = content[0]
            dic['id'] = ''
            dic['time'] = content[1]
            data = json.dumps(dic)
            # 체크가 안된 자리 번호를 백엔드로 전송
            r = requests.post(url+'rfid/', data=data)
            if r.status_code == 200:
                status[content[0]] = 30
                return True
            else:
                log.append(data)
            
        return False
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
        if d > SEAT_LENGTH:
            status[num] = 0
            return
        elif d > (SEAT_LENGTH / 2):
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
                t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
                s_t = threading.Thread(target=send, args=(10, (parkingSpotID[num], t)))
                s_t.start()
                return


# 500cm 기준으로 10초마다 체크
# 500cm 안쪽이 감지된 경우 1초마다 체크
# 프로토타입의 경우 20cm 기준, 기본 상태에서 5초마다 체크
def ultrasonic():
    distance = [None for i in range(SENSOR_NUM)]
    n = [0 for i in range(SENSOR_NUM)]

    while True:
        for i in range(SENSOR_NUM):
            if status[i] == 0:
                distance[i] = us[i].run()
                print("기본({}) : 상태 {}, 측정거리 {:.2f}".format(i, status[i], distance[i]))
                if distance[i] < SEAT_LENGTH:
                    status[i] = 1
                    # detect를 스레드로 실행
                    detect_t = threading.Thread(target=detect, args=(i,))
                    detect_t.start()
            elif status[i] == 2 or status[i] == 3 or status[i] == 30 or status[i] == 31 or status[i] == 4:
                distance[i] = us[i].run()
                print("기본({}) : 상태 {}, 측정거리 {:.2f}".format(i, status[i], distance[i]))
                if distance[i] > SEAT_LENGTH:
                    n[i] += 1
                    if n[i] == 3:
                        status[i] = 0
                        n[i] = 0
                        t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
                        s_t = threading.Thread(target=send, args=(11, [parkingSpotID[i], t]))
                        s_t.start()
                else:
                    n[i] = 0

        time.sleep(10)


# 각 자리의 상태 확인 -> rfid 활성화가 필요한 자리의
def rfid():
    active_num = []
    last = [0 for i in range(SENSOR_NUM)]
    start_time = [-1 for i in range(SENSOR_NUM)]
    RC522 = MFRC522_multi.MFRC522(rfid)

    while True:
        # 이전 상태와 현재 상태 비교, 필요한 처리를 한 후 현재 상태를 배열에 기록
        for i in range(SENSOR_NUM):
            if last[i] == status[i]:            # 상태가 동일한 경우 다음 센서로 넘어감
                continue
            else:                               # 상태가 다른 경우
                if status[i] != 3:                  # 현재 상태가 3(rfid 인식 대기)이 아닌 경우
                    start_time[i] = -1              # 센서시작시간 기록을 초기화
                else:                               # 현재 상태가 3(rfid 인식 대기)인 경우
                    start_time[i] = time.time()     # 현재 시간을 센서시작시간으로 기록

            last[i] = status[i]

        active_num.clear()
        for i in range(SENSOR_NUM):
            if status[i] == 3:
                active_num.append(rfid[i])
        result = multi_read.read(RC522, rfid)

        # result의 결과값에서 -1이 아닌 값만 처리
        for p in result:
            index = rfid.index(p)
            if time.time() - start_time[index] > TIME_LIMIT:
                t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
                s_t = threading.Thread(target=send, args=(21, [parkingSpotID[index], t]))
                s_t.start()
            if result[p] != -1:
                print(f'sensor {index} : {result[p]}')
                # 백엔드에 값을 보내서 확인하는 로직
                t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
                s_t = threading.Thread(target=send, args=(20, [parkingSpotID[index], result[p], t]))
                s_t.start()


if __name__ == '__main__':
    try:
        p_led = multiprocessing.Process(target=led)
        p_us = multiprocessing.Process(target=ultrasonic)
        p_rfid = multiprocessing.Process(target=rfid)

        p_led.start()
        p_us.start()
        p_rfid.start()
        
        uvicorn.run(app, host="0.0.0.0", port=8000)

        p_led.join()
        p_us.join()
        p_rfid.join()

    except KeyboardInterrupt:
        status.shm.close()
        status.shm.unlink()
        GPIO.cleanup()
