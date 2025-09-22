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
from users.async_tasks import crawl_timetable_task, crawl_events_task
from celery.result import AsyncResult
import shutil

# log test
import logging

# 로거 설정
logger = logging.getLogger("schedulo")  # myapp 로거를 사용

from contextlib import contextmanager
import os

# ChromeDriver 경로 설정 (서버 환경에 맞게 조정)
CHROMEDRIVER_PATH = os.environ.get("CHROMEDRIVER", "/usr/bin/chromedriver")

# ChromeDriver 존재 확인
if not os.path.exists(CHROMEDRIVER_PATH):
    logger.warning(
        f"ChromeDriver not found at {CHROMEDRIVER_PATH}, using ChromeDriverManager"
    )
    CHROMEDRIVER_PATH = None  # ChromeDriverManager 사용


# chromedriver 설정 함수
@contextmanager
def get_driver():
    tmpdir = None
    try:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp/chrome-runtime"
        os.makedirs(runtime_dir, exist_ok=True)
        os.chmod(runtime_dir, 0o700)  # 디렉토리 권한 설정
        os.environ["XDG_RUNTIME_DIR"] = runtime_dir

        tmpdir = tempfile.mkdtemp(prefix="chrome-profile-")  # 요청별 고유 디렉토리
        data_path = os.path.join(tmpdir, "data")
        cache_path = os.path.join(tmpdir, "cache")

        options = Options()
        options.add_argument("--headless=new")  # Headless 모드 설정
        options.add_argument("--lang=ko-KR")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
        options.add_argument("--disable-gpu")  # GPU 가속 비활성화

        # --user-data 중복 방지
        options.add_argument(f"--user-data-dir={tmpdir}")
        options.add_argument(f"--data-path={data_path}")
        options.add_argument(f"--disk-cache-dir={cache_path}")
        options.add_argument("--remote-debugging-port=9222")

        # ChromeDriver 경로에 따라 Service 설정
        if CHROMEDRIVER_PATH:
            service = Service(executable_path=CHROMEDRIVER_PATH)
        else:
            service = Service(executable_path=ChromeDriverManager().install())

        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            yield driver
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass
    finally:
        # 4. tmpdir이 유효할 경우에만 삭제
        if tmpdir and os.path.exists(tmpdir):
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


##시간표 불러오기 (비동기)
class GetTimeTableView(APIView):
    def get(self, request):
        try:
            # Celery 태스크 시작
            task = crawl_timetable_task.delay(request.user.id)

            logger.info(
                f"시간표 크롤링 태스크 시작 - 사용자: {request.user.email}, 태스크 ID: {task.id}"
            )

            return Response(
                {
                    "message": "시간표 불러오기를 시작했습니다. 완료되면 알림을 받으실 수 있습니다.",
                    "task_id": task.id,
                    "status": "STARTED",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(
                f"시간표 크롤링 태스크 시작 실패 - 사용자: {request.user.email}, 오류: {e}"
            )
            return Response(
                {"message": "시간표 불러오기 시작에 실패했습니다.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


##시간표 크롤링 상태 확인
class TimeTableTaskStatusView(APIView):
    def get(self, request):
        """
        시간표 크롤링 태스크의 상태를 확인합니다.
        """
        task_id = request.GET.get("task_id")

        if not task_id:
            return Response(
                {"message": "task_id가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Celery 태스크 결과 조회
            task_result = AsyncResult(task_id)

            if task_result.state == "PENDING":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "대기 중...",
                    "progress": 0,
                }
            elif task_result.state == "PROGRESS":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": task_result.info.get("status", "진행 중..."),
                    "progress": task_result.info.get("progress", 0),
                }
            elif task_result.state == "SUCCESS":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "완료",
                    "progress": 100,
                    "result": task_result.result,
                }

            elif task_result.state == "FAILURE":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "실패",
                    "error": str(task_result.info),
                }
            else:
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "알 수 없는 상태",
                    "progress": 0,
                }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"태스크 상태 확인 실패 - 태스크 ID: {task_id}, 오류: {e}")
            return Response(
                {"message": "태스크 상태 확인에 실패했습니다.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


##일정 크롤링 상태 확인
class EventsTaskStatusView(APIView):
    def get(self, request):
        """
        일정 크롤링 태스크의 상태를 확인합니다.
        """
        task_id = request.GET.get("task_id")

        if not task_id:
            return Response(
                {"message": "task_id가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Celery 태스크 결과 조회
            task_result = AsyncResult(task_id)

            if task_result.state == "PENDING":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "대기 중...",
                    "progress": 0,
                }
            elif task_result.state == "PROGRESS":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": task_result.info.get("status", "진행 중..."),
                    "progress": task_result.info.get("progress", 0),
                }
            elif task_result.state == "SUCCESS":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "완료",
                    "progress": 100,
                    "result": task_result.result,
                }

                # 해당 task에서 저장된 일정 리스트만 반환
                try:
                    from schedules.models import Schedule

                    # task 결과에서 저장된 일정 ID 목록 가져오기
                    saved_schedule_ids = task_result.result.get(
                        "saved_schedule_ids", []
                    )

                    if saved_schedule_ids:
                        # 해당 ID들로 일정 조회 (태그 정보 포함)
                        saved_schedules = (
                            Schedule.objects.filter(id__in=saved_schedule_ids)
                            .select_related()
                            .prefetch_related("tag")
                            .order_by("-scheduled_date", "title")
                        )

                        # 간단한 형태로 변환 (id, title, scheduled_date, tag_name만)
                        simple_schedules = []
                        for schedule in saved_schedules:
                            # 태그 이름들 가져오기 (첫 번째 태그만)
                            tag_name = (
                                schedule.tag.first().name
                                if schedule.tag.exists()
                                else None
                            )

                            simple_schedules.append(
                                {
                                    "id": schedule.id,
                                    "title": schedule.title,
                                    "scheduled_date": schedule.scheduled_date.strftime(
                                        "%Y-%m-%d"
                                    ),
                                    "tag_name": tag_name,
                                }
                            )

                        response_data["saved_schedules"] = simple_schedules
                        response_data["saved_schedules_count"] = len(simple_schedules)
                    else:
                        response_data["saved_schedules"] = []
                        response_data["saved_schedules_count"] = 0

                except Exception as e:
                    logger.error(f"저장된 일정 리스트 조회 실패: {e}")
                    response_data["saved_schedules"] = []
                    response_data["saved_schedules_count"] = 0

            elif task_result.state == "FAILURE":
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "실패",
                    "error": str(task_result.info),
                }
            else:
                response_data = {
                    "task_id": task_id,
                    "state": task_result.state,
                    "status": "알 수 없는 상태",
                    "progress": 0,
                }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"태스크 상태 확인 실패 - 태스크 ID: {task_id}, 오류: {e}")
            return Response(
                {"message": "태스크 상태 확인에 실패했습니다.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ecampus 일정 불러오기 (비동기)
class CrawlingView(APIView):
    def get(self, request):

        try:
            # Celery 태스크 시작
            task = crawl_events_task.delay(request.user.id)

            logger.info(
                f"일정 크롤링 태스크 시작 - 사용자: {request.user.email}, 태스크 ID: {task.id}"
            )

            return Response(
                {
                    "message": "일정 불러오기를 시작했습니다. 완료되면 알림을 받으실 수 있습니다.",
                    "task_id": task.id,
                    "status": "STARTED",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(
                f"일정 크롤링 태스크 시작 실패 - 사용자: {request.user.email}, 오류: {e}"
            )
            return Response(
                {"message": "일정 불러오기 시작에 실패했습니다.", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
