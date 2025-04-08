from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

import datetime
from datetime import datetime
from bs4 import BeautifulSoup
from django.views import View
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from rest_framework.response import Response
from rest_framework import status

from schedules.models import Schedule, Tag, TimeTable
from schedules.serializers import ScheduleSerializer
from users.utils import (
    check_error,
    get_courses,
    get_events,
    get_syllabus,
    login_attempt,
    save_to_timetable,
)


# chromedriver 설정 함수
def get_driver():
    options = Options()
    options.add_argument("--headless")  # Headless 모드 설정
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
    options.add_argument("--disable-gpu")  # GPU 가속 비활성화

    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    service = Service(executable_path=ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


# 학번, 비밀번호 유효성 검사
class StudentInfoCheckView(APIView):
    def post(self, request):
        student_id = request.data.get("student_id")
        student_password = request.data.get("student_password")

        driver = get_driver()
        try:
            # ecampus login
            login_attempt(driver, student_id, student_password)
            if check_error(driver):
                return Response(
                    {"message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"message": "올바른 학번, 비밀번호 입니다."}, status=status.HTTP_200_OK
            )
        finally:
            driver.quit()


##시간표 불러오기
class GetTimeTableView(APIView):
    def get(self, request):
        student_id = self.request.user.student_id
        student_password = self.request.user.get_student_password()

        driver = get_driver()
        try:
            # ecampus login
            login_attempt(driver, student_id, student_password)
            if check_error(driver):
                return Response(
                    {"message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                print("✅ 로그인 성공!")

            # 과목 불러오기
            courses = get_courses(driver)
            if not courses:
                return Response(
                    {"message": "❌ 과목 정보를 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            courses_data = []
            print("\n📚 수강 중인 과목 목록:")
            for course_title, course_id in courses:
                # 시간표 데이터 조회
                course_name, course_time, schedules = get_syllabus(driver, course_id)
                display_name = (
                    course_name if course_name != "정보 없음" else course_title
                )

                if course_time != "정보 없음":
                    print(f"  - {display_name}")
                    print(f"    🕒 강의시간: {course_time}")
                    if schedules:
                        # Explicitly append a 2-tuple
                        courses_data.append((display_name, schedules))

            # 시간표 저장
            save_to_timetable(self, request.user, courses_data)

            return Response(
                {
                    "message": "✅시간표 불러오기 및 저장 성공",
                    "courses_data": courses_data,
                },
                status=status.HTTP_200_OK,
            )
        finally:
            driver.quit()


# ecampus 일정 불러오기
class CrawlingView(APIView):
    def get(self, request):
        student_id = self.request.user.student_id
        student_password = self.request.user.get_student_password()

        driver = get_driver()
        try:
            # ecampus login
            login_attempt(driver, student_id, student_password)
            if check_error(driver):
                return Response(
                    {"message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            print("✅ 로그인 성공")

            # 일정 불러오기
            course_events = get_events(driver, request.user.id)
            if not course_events:
                return Response(
                    {"message": "새로운 일정이 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "message": "일정을 모두 불러왔습니다.",
                    "courses": course_events,  # 중복 제외한 과목 정보 반환
                },
                status=status.HTTP_200_OK,
            )
        finally:
            driver.quit()
