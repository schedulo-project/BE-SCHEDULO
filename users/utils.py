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


# log test
import logging

# 로거 설정
logger = logging.getLogger("schedulo")  # myapp 로거를 사용


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
        logger.error("❌ 로그인 실패:", error_message.text)
        return True
    except:
        return False


def get_courses(driver):
    """수강 중인 과목 정보"""
    driver.get("https://ecampus.smu.ac.kr/")

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.my-course-lists"))
        )
    except Exception as e:
        logger.error("과목 리스트 로딩 실패: %s", e)
        return []

    soup = BeautifulSoup(driver.page_source, "lxml")

    # 과목 리스트 찾기
    courses = soup.select("ul.my-course-lists > li > div.course_box > a.course_link")

    if not courses:
        logger.warning("❌ 과목 정보를 찾을 수 없습니다.")
        return

    course_info = []
    for course in courses:
        title_el = course.select_one("div.course-title > h3")
        if title_el:
            course_title = title_el.get_text(strip=True)
            course_id = course["href"].split("=")[-1]
            course_info.append((course_title, course_id))

    return course_info


def get_syllabus(driver, course_id):
    """강의 계획서에서 시간표 데이터를 반환"""
    syllabus_url = (
        f"https://ecampus.smu.ac.kr/local/ubion/setting/syllabus.php?id={course_id}"
    )

    try:
        driver.get(syllabus_url)
        # WebDriverWait(driver, 5).until(
        #     EC.presence_of_element_located((By.TAG_NAME, "table"))
        # )
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "region-main"))
        )
    except Exception as e:
        logger.error("강의 계획서 로딩 실패: %s", e)
        return "정보 없음", "정보 없음", []

    soup = BeautifulSoup(driver.page_source, "lxml")

    # 강의계획서가 없는 경우 (텍스트 기반 체크)
    if soup.find(string=re.compile("등록된 강의계획서가 없습니다")):
        logger.info(f"❌ 강의계획서 없음: {course_id}")
        return "정보 없음", "정보 없음", []

    try:

        # "교과목명" 파싱
        course_name_th = soup.find("th", string=re.compile("교과목명"))
        course_name = (
            course_name_th.find_next("td").get_text(strip=True)
            if course_name_th
            else "정보 없음"
        )

        # "강의시간" 파싱
        course_time_th = soup.find("th", string=re.compile("강의시간"))
        course_time = (
            course_time_th.find_next("td").get_text(strip=True)
            if course_time_th
            else "정보 없음"
        )

        # 시간표 정보 정제
        schedules = []
        if course_time != "정보 없음":
            for slot in course_time.split():
                match = re.match(
                    r"([월화수목금토일])(\d+(?:,\d+)*|\d+-\d+)\((.*?)\)", slot
                )
                if not match:
                    logger.warning(f"⚠️ 강의시간 파싱 실패: {slot}")
                    continue

                day, periods_part, location = match.groups()
                periods = (
                    list(map(int, periods_part.split(",")))
                    if "," in periods_part
                    else (
                        list(range(*map(int, periods_part.split("-"))))
                        if "-" in periods_part
                        else [int(periods_part)]
                    )
                )

                for period in periods:
                    start_hour = period + 8
                    end_hour = start_hour + 1
                    time_range = f"{start_hour:02d}:00~{end_hour:02d}:00"
                    schedules.append((day, time_range, location))

        return course_name, course_time, schedules

    except Exception as e:
        logger.error(f"⚠️ 강의계획서 파싱 오류 - {course_id}: {e}")
        return "정보 없음", "정보 없음", []


def save_to_timetable(self, user, courses_data):
    """Save courses_data into the TimeTable model without duplicates."""
    day_map = {
        "월": "mon",
        "화": "tue",
        "수": "wed",
        "목": "thu",
        "금": "fri",
        "토": "sat",
        "일": "sun",
    }

    for course_name, schedules in courses_data:
        for day, time_range, location in schedules:
            start_str, end_str = time_range.split("~")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            day_of_week = day_map[day]  # Convert Korean day to English abbreviation

            subject = course_name[:30] if len(course_name) > 30 else course_name

            tag, created = Tag.objects.get_or_create(name=subject, user=user)
            if created:
                logger.info(f"✅ 태그 저장: {tag.name}")

            # Check for existing entry to avoid duplicates
            existing_entry = TimeTable.objects.filter(
                subject=subject,
                user=user,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
            ).exists()

            if not existing_entry:
                TimeTable.objects.create(
                    subject=subject,
                    user=user,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                )
                logger.info(
                    f"✅ 과목정보 저장:: {subject} ({day_of_week}: {start_time} - {end_time})"
                )


def get_all_first_semester_courses(driver, semester):
    """드롭다운에서 수강하는 강좌 가져오기"""
    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "select.select.autosubmit.cal_courses_flt")
        )
    )
    select = Select(select_element)
    return [option.text for option in select.options if f"[{semester}]" in option.text]


def get_events_for_course(driver, course_text):
    """특정 강좌의 이벤트를 가져오기"""
    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "select.select.autosubmit.cal_courses_flt")
        )
    )
    select = Select(select_element)
    select.select_by_visible_text(course_text)

    soup = BeautifulSoup(driver.page_source, "lxml")
    date_elements = soup.select("div.day a")
    event_lists = soup.select("ul.events-new")

    events_by_date = {}
    for i, date_text in enumerate([date.get_text().strip() for date in date_elements]):
        try:
            events = event_lists[i].select("li.calendar_event_course a")
            event_texts = [event.get_text().strip() for event in events]
            if event_texts:
                events_by_date[date_text] = event_texts
        except IndexError:
            continue
    return events_by_date


def move_to_next_month(driver):
    next_month_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.arrow_link.next"))
    )
    next_month_button.click()
    time.sleep(1)
    logger.debug("➡️ 다음 달로 이동했습니다.")


def get_events(driver, user, year=None, months=None):
    """학기 중 일정"""
    if year is None:
        year = datetime.now().year

    current_month = datetime.now().month

    # 학기 정의
    SEMESTER_1 = range(3, 7)  # 3월~6월 (1학기)
    SEMESTER_2 = range(9, 13)  # 9월~12월 (2학기)

    if months is None:
        if current_month in SEMESTER_1:
            start_month = current_month
            end_month = 6
            semester_name = "1학기"
        elif current_month in SEMESTER_2:
            start_month = current_month
            end_month = 12
            semester_name = "2학기"
        else:
            logger.debug(
                f"📅 현재 {current_month}월은 학기 중이 아닙니다. (1학기: 3~6월, 2학기: 9~12월)"
            )
            return

        months = list(range(start_month, end_month + 1))

    # 과목별 이벤트 저장
    course_events = {}

    for month in months:
        start_date = datetime(year, month, 1)
        timestamp = calendar.timegm(start_date.timetuple())
        url = f"https://ecampus.smu.ac.kr/calendar/view.php?view=month&course=1&time={timestamp}"
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "lxml")
        year_month = soup.select_one("h2.current").get_text().strip()
        logger.debug(f"\n📅 {year_month} 이벤트")

        # 수업이 아닌 항목 제외
        first_semester_courses = get_all_first_semester_courses(driver, semester_name)
        if not first_semester_courses:
            logger.debug("❌ 수강하는 강좌가 없습니다.")
            move_to_next_month(driver)
            continue

        for course_text in first_semester_courses:
            logger.debug(f"선택된 강좌: {course_text}")
            # get events
            events = get_events_for_course(driver, course_text)

            subject_name = (
                re.search(r"\](.*?)\(", course_text).group(1).strip()
                if re.search(r"\](.*?)\(", course_text)
                else course_text
            )
            tag, _ = Tag.objects.get_or_create(name=subject_name, user=user)

            # 과목별 이벤트 저장
            if subject_name not in course_events:
                course_events[subject_name] = []

            for date, event_list in events.items():
                scheduled_date = datetime(year, month, int(date)).date()
                logger.debug(f"\n📅 {scheduled_date}")
                for event in event_list:
                    logger.debug(f"  - {event}")
                    # 중복 체크
                    if not Schedule.objects.filter(
                        user=user, scheduled_date=scheduled_date, title=event
                    ).exists():
                        data = {
                            "title": event,
                            "scheduled_date": scheduled_date,
                            "user": user,
                        }
                        serializer = ScheduleSerializer(
                            data=data, context={"request": None}
                        )
                        if serializer.is_valid():
                            schedule = serializer.save()
                            # save_tags
                            schedule.tag.add(tag)
                            logger.debug(f" ✅ 저장됨: {event}")
                            course_events[subject_name].append(
                                {
                                    "title": event,
                                    "scheduled_date": scheduled_date,
                                }
                            )
                        else:
                            logger.warning(f"  저장 실패: {serializer.errors}")
                    else:
                        logger.debug(f"  중복 데이터 스킵: {event}")
            if not events:
                logger.debug("  (이벤트 없음)")

        move_to_next_month(driver)

    return course_events
