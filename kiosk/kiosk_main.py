#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
키오스크 라즈베리파이 제어용 메인 파일
웹페이지 작동
서버 통신, 센서 인식, 솔레노이드 작동

백에서 파이로 요청을 보내는 경우
 - rfid 태그 활성화 요청
 - 보관함 열기 요청

상태별 led
    0 = 소등
    1 = 흰색 점멸
'''


import RPi.GPIO as GPIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

import multiprocessing
from multiprocessing import shared_memory
import json

from solenoid import *
import MFRC522_single
import single_read


#TIME_LIMIT = 60         # RFID 리더기 인식 제한 시간
TIME_LIMIT = 10          # 프로토타입 RFID 리더기 인식 제한 시간


webpage_url = 'https://google.com/'
url = ''
box = [14, 15, 18]
box_led = [2, 3, 4]
sol = solenoid(box, box_led)

# 상태 저장 리스트 [ led 상태(0, 1, 10, 11, 2) ]
status = shared_memory.ShareableList([0]);

manager = multiprocessing.Manager()

# 백엔드 연결 후 통신 실패시 로그 기록용 리스트
log = manager.list()

class Item(BaseModel):
    num: int

app = FastAPI()

@app.post("/")
async def rfid_activation():
    status[0] = 1
    return True

@app.post("/rfid_return/")
async def rfid_return():
    info = rfid()
    
    dic = {}
    dic['type'] = info[0]
    dic['id'] = info[1]
    dic['time'] = info[2]
    data = json.dumps(dic)
    
    return data

@app.post("/receive-car-key/")
async def boxopen(item: Item, background_tasks: BackgroundTasks):
    print(item.num)
    print(type(item.num))
    background_tasks.add_task(sol.box_open, item.num)
    return  { 'box_number' : item }

@app.post("/return-car-key/")
async def boxopen(item: Item, background_tasks: BackgroundTasks):
    status[0] = 0
    print(item.num)
    print(type(item.num))
    background_tasks.add_task(sol.box_open, item.num)
    return  { 'box_number' : item }


def led():
    last = 0
    led = [17, 27, 22]
    n = 0
    
    GPIO.setmode(GPIO.BCM)
    for i in led:
        GPIO.setup(i, GPIO.OUT)
    
    def on(r, g, b):   # r, g, b 색상별로 on, off 하는 함수
        GPIO.output(led[0], r)
        GPIO.output(led[1], g)
        GPIO.output(led[2], b)

    def off():           # led를 끄는 함수
        GPIO.output(led[0], 0)
        GPIO.output(led[1], 0)
        GPIO.output(led[2], 0)
    
    while True:
        if status[0] != last:
            n = 0
        last = status[0]
        
        if last == 0:
            off()
        elif last == 1:
            on(1, 1, 1)

        time.sleep(0.5)

        if last == 1:
            off()

        time.sleep(0.5)


def rfid():
    start_time = time.time()
    RC522 = MFRC522_single.MFRC522(25)
    status[0] = 1
    
    while True:
        result = single_read.read(RC522)
        if time.time() - start_time > TIME_LIMIT:
            status[0] = 0
            t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
            return [False, '', t]
        if result != -1:
            print(f'sensor : {result}')
            status[0] = 0
            t = time.strftime('%Y-%m-%dT%I:%M:%S', time.localtime())
            return [True, result, t]
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        options = Options()
        options.add_argument('--kiosk')
        driver = webdriver.Chrome(options=options)
        driver.get(webpage_url)   
        
        p_led = multiprocessing.Process(target=led)
        
        p_led.start()
        
        uvicorn.run(app, host="0.0.0.0", port=8888)
        
        p_led.join()

    except KeyboardInterrupt:
        status.shm.close()
        status.shm.unlink()
        driver.close()
        GPIO.cleanup()