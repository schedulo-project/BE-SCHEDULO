from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import Select
import datetime
from datetime import datetime
import calendar
import re

from schedules.models import Schedule, Tag, TimeTable
from schedules.serializers import ScheduleSerializer


def login_attempt(driver, USER_ID, USER_PW):
    """ecampus 로그인 실행"""
    driver.get("https://ecampus.smu.ac.kr/login.php")  # 로그인 페이지 URL
    # 아이디, 비밀번호 입력란 찾기
    username_input = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    password_input = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.NAME, "password"))
    )
    username_input.send_keys(USER_ID)
    password_input.send_keys(USER_PW)

    # 로그인 버튼 클릭
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, "loginbutton"))
    )
    login_button.click()


def check_error(driver):
    """로그인 실패 여부 확인"""
    try:
        error_message = driver.find_element(
            By.XPATH, '//*[@id="region-main"]/div/div/div/div[1]/div[1]/div[2]/form/p'
        )
        print("❌ 로그인 실패:", error_message.text)
        return True
    except:
        return False
