from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from users.utils import (
    check_error,
    get_courses,
    get_syllabus,
    login_attempt,
    save_to_timetable,
)
from schedules.models import TimeTable
from notifications.utils import send_multi_channel
import shutil
from contextlib import contextmanager

User = get_user_model()
logger = logging.getLogger("schedulo")


@contextmanager
def get_driver():
    tmpdir = tempfile.mkdtemp(prefix="chrome-profile-")
    driver = None
    try:
        options = Options()
        # options.add_argument("--headless=new")  # Headless 모드 설정
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

        service = Service(executable_path=ChromeDriverManager().install())
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


@shared_task(bind=True)
def crawl_timetable_task(self, user_id):
    try:
        # 태스크 상태 업데이트
        self.update_state(
            state="PROGRESS",
            meta={"status": "시간표 크롤링을 시작합니다...", "progress": 10},
        )

        # 사용자 정보 조회
        user = User.objects.get(id=user_id)
        student_id = user.student_id
        student_password = user.get_student_password()

        logger.info(f"시간표 크롤링 시작 - 사용자: {user.username} (ID: {user_id})")

        # WebDriver 설정
        with get_driver() as driver:
            try:
                # 태스크 상태 업데이트
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "eCampus 로그인 중...", "progress": 20},
                )

                # eCampus 로그인
                login_attempt(driver, student_id, student_password)
                if check_error(driver):
                    error_msg = "로그인 실패: 학번 또는 비밀번호가 잘못되었습니다."
                    logger.error(f"로그인 실패 - 사용자: {user.username}")
                    return {
                        "status": "FAILURE",
                        "message": error_msg,
                        "error": error_msg,
                    }

                logger.info("✅ 로그인 성공!")

                # 태스크 상태 업데이트
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "과목 정보를 불러오는 중...", "progress": 40},
                )

                # 과목 불러오기
                courses = get_courses(driver)
                if not courses:
                    error_msg = "과목 정보를 찾을 수 없습니다."
                    logger.warning(f"과목 정보 없음 - 사용자: {user.username}")
                    return {
                        "status": "FAILURE",
                        "message": error_msg,
                        "error": error_msg,
                    }

                # 태스크 상태 업데이트
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "시간표 정보를 파싱하는 중...", "progress": 60},
                )

                courses_data = []
                logger.debug("\n📚 수강 중인 과목 목록:")
                for course_title, course_id in courses:
                    # 시간표 데이터 조회
                    course_name, course_time, schedules = get_syllabus(
                        driver, course_id
                    )
                    display_name = (
                        course_name if course_name != "정보 없음" else course_title
                    )

                    if course_time != "정보 없음":
                        logger.debug(f"  - {display_name}")
                        logger.debug(f"    🕒 강의시간: {course_time}")
                        if schedules:
                            courses_data.append((display_name, schedules))

                # 크롤링된 데이터가 있을 때만 기존 데이터 삭제
                if courses_data:
                    # 태스크 상태 업데이트
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": "기존 시간표 데이터를 삭제하는 중...",
                            "progress": 75,
                        },
                    )

                    # 기존 시간표 데이터 삭제 (크롤링 성공 후에만)
                    deleted_count = TimeTable.objects.filter(user=user).count()
                    TimeTable.objects.filter(user=user).delete()
                    logger.info(
                        f"🗑️ 기존 시간표 데이터 {deleted_count}개 삭제 완료 - 사용자: {user.username}"
                    )
                else:
                    deleted_count = 0
                    logger.warning(
                        f"⚠️ 크롤링된 데이터가 없어 기존 데이터를 삭제하지 않습니다 - 사용자: {user.username}"
                    )

                # 크롤링된 데이터가 있을 때만 저장
                if courses_data:
                    # 태스크 상태 업데이트
                    self.update_state(
                        state="PROGRESS",
                        meta={"status": "시간표를 저장하는 중...", "progress": 80},
                    )

                    # 시간표 저장
                    save_to_timetable(None, user, courses_data)

                # 태스크 상태 업데이트
                self.update_state(
                    state="PROGRESS", meta={"status": "완료!", "progress": 100}
                )

                # 결과 처리
                if courses_data:
                    result = {
                        "status": "SUCCESS",
                        "message": "시간표 불러오기 및 저장이 완료되었습니다.",
                        "courses_count": len(courses_data),
                        "deleted_count": deleted_count,
                        "courses_data": courses_data,
                    }

                    logger.info(
                        f"✅ 시간표 크롤링 완료 - 사용자: {user.username}, 삭제된 데이터: {deleted_count}개, 새로 저장된 과목 수: {len(courses_data)}"
                    )

                    # 완료 알림 전송
                    try:
                        send_multi_channel(
                            user=user,
                            title="📅 시간표 불러오기 완료",
                            body=f"{len(courses_data)}개의 과목 시간표가 성공적으로 불러와졌습니다!",
                        )
                        logger.info(f"완료 알림 전송 - 사용자: {user.username}")
                    except Exception as e:
                        logger.error(
                            f"알림 전송 실패 - 사용자: {user.username}, 오류: {e}"
                        )
                else:
                    result = {
                        "status": "SUCCESS",
                        "message": "시간표 크롤링이 완료되었지만 저장할 데이터가 없습니다.",
                        "courses_count": 0,
                        "deleted_count": deleted_count,
                        "courses_data": [],
                    }

                    logger.warning(
                        f"⚠️ 시간표 크롤링 완료 - 사용자: {user.username}, 저장할 데이터 없음, 기존 데이터 유지"
                    )

                    # 알림 전송
                    try:
                        send_multi_channel(
                            user=user,
                            title="📅 시간표 불러오기 완료",
                            body="시간표 크롤링이 완료되었지만 저장할 데이터가 없어 기존 데이터를 유지합니다.",
                        )
                        logger.info(f"알림 전송 - 사용자: {user.username}")
                    except Exception as e:
                        logger.error(
                            f"알림 전송 실패 - 사용자: {user.username}, 오류: {e}"
                        )

                return result

            except Exception as e:
                error_msg = f"시간표 크롤링 중 오류가 발생했습니다: {str(e)}"
                logger.error(f"시간표 크롤링 오류 - 사용자: {user.username}, 오류: {e}")
                return {"status": "FAILURE", "message": error_msg, "error": str(e)}

    except User.DoesNotExist:
        error_msg = f"사용자를 찾을 수 없습니다. (ID: {user_id})"
        logger.error(error_msg)
        return {"status": "FAILURE", "message": error_msg, "error": error_msg}

    except Exception as e:
        error_msg = f"시간표 크롤링 중 오류가 발생했습니다: {str(e)}"
        logger.error(f"시간표 크롤링 오류 - 사용자 ID: {user_id}, 오류: {e}")
        return {"status": "FAILURE", "message": error_msg, "error": str(e)}
