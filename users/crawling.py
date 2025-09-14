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
from users.timetable_tasks import crawl_timetable_task
from celery.result import AsyncResult
import shutil

# log test
import logging

# 로거 설정
logger = logging.getLogger("schedulo")  # myapp 로거를 사용

CHROMEDRIVER_PATH = "/usr/bin/chromedriver"

from contextlib import contextmanager


# chromedriver 설정 함수
@contextmanager
def get_driver():
    tmpdir = tempfile.mkdtemp(prefix="chrome-profile-")  # 요청별 고유 디렉토리
    driver = None
    try:
        options = Options()
        options.add_argument("--headless=new")  # Headless 모드 설정
        options.add_argument("--lang=ko-KR")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
        options.add_argument("--disable-gpu")  # GPU 가속 비활성화

        # --user-data 중복 방지
        options.add_argument(f"--user-data-dir={tmpdir}")
        options.add_argument(f"--data-path={tmpdir}/data")
        options.add_argument(f"--disk-cache-dir={tmpdir}/cache")
        options.add_argument("--remote-debugging-port=0")

        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        yield driver
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass
        shutil.rmtree(tmpdir, ignore_errors=True)


# 학번, 비밀번호 유효성 검사
class StudentInfoCheckView(APIView):
    def post(self, request):
        student_id = request.data.get("student_id")
        student_password = request.data.get("student_password")

        with get_driver() as driver:
            try:
                # ecampus login
                login_attempt(driver, student_id, student_password)
                if check_error(driver):
                    return Response(
                        {
                            "message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {"message": "올바른 학번, 비밀번호 입니다."},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.error(f"StudentInfoCheckView 오류: {e}")
                return Response(
                    {"message": "로그인 검증 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


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
                logger.info("✅ 로그인 성공!")

            # 과목 불러오기
            courses = get_courses(driver)
            if not courses:
                return Response(
                    {"message": "❌ 과목 정보를 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            courses_data = []
            logger.debug("\n📚 수강 중인 과목 목록:")
            for course_title, course_id in courses:
                # 시간표 데이터 조회
                course_name, course_time, schedules = get_syllabus(driver, course_id)
                display_name = (
                    course_name if course_name != "정보 없음" else course_title
                )

                if course_time != "정보 없음":
                    logger.debug(f"  - {display_name}")
                    logger.debug(f"    🕒 강의시간: {course_time}")
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

        with get_driver() as driver:
            try:
                # ecampus login
                login_attempt(driver, student_id, student_password)
                if check_error(driver):
                    return Response(
                        {
                            "message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                logger.info("✅ 로그인 성공")

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
            except Exception as e:
                logger.error(f"CrawlingView 오류: {e}")
                return Response(
                    {"message": "일정 불러오기 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
