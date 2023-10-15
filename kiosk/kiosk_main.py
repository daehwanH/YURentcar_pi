'''
키오스크 라즈베리파이 제어용 메인 파일
웹페이지 작동
서버 통신, 센서 인식, 솔레노이드 작동

백에서 파이로 요청을 보내는 경우
 - rfid 태그 활성화 요청
 - 보관함 열기 요청
'''


import RPi.GPIO as GPIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import uvicorn
from fastapi import BackgroundTasks, FastAPI
from solenoid import *


URL = "https://google.com"
box = [14, 15, 18]
led = [2, 3, 4]
sol = solenoid(box, led)


app = FastAPI()

@app.post("/open")
async def boxopen(num : str, background_tasks: BackgroundTasks):
    background_tasks.add_task(sol.box_open, int(num))
    return  { 'box number' : num }


if __name__ == "__main__":
    try:
        options = Options()
        options.add_argument('--kiosk')
        driver = webdriver.Chrome(options=options)
        driver.get(URL)

        uvicorn.run(app, host="127.0.0.1", port=8000)

    except KeyboardInterrupt:
        GPIO.cleanup()