from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

import datetime
from datetime import datetime
from bs4 import BeautifulSoup
from django.views import View
from selenium import webdriver
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


# 학번, 비밀번호 유효성 검사
class StudentInfoCheckView(APIView):
    def post(self, request):
        student_id = request.data.get("student_id")
        student_password = request.data.get("student_password")

        driver = webdriver.Chrome()
        # ecampus login
        login_attempt(driver, student_id, student_password)
        if check_error(driver):
            driver.quit()
            return Response(
                {"message": "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            driver.quit()
            return Response(
                {"message": "올바른 학번, 비밀번호 입니다."}, status=status.HTTP_200_OK
            )


##시간표 불러오기
class GetTimeTableView(APIView):
    def get(self, request):
        student_id = self.request.user.student_id
        student_password = self.request.user.get_student_password()

        driver = webdriver.Chrome()
        try:
            # ecampus login
            login_attempt(driver, student_id, student_password)
            if check_error(driver):
                driver.quit()
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
