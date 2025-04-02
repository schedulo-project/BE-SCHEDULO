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


def get_courses(driver):
    """수강 중인 과목 정보"""
    driver.get("https://ecampus.smu.ac.kr/")

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "lxml")

    # 과목 리스트 찾기
    courses = soup.select("ul.my-course-lists > li > div.course_box > a.course_link")

    if not courses:
        print("❌ 과목 정보를 찾을 수 없습니다.")
        return

    course_info = []
    for course in courses:
        course_title = course.select_one("div.course-title > h3").get_text(strip=True)
        course_id = course["href"].split("=")[-1]
        course_info.append((course_title, course_id))

    return course_info


def get_syllabus(driver, course_id):
    """강의 계획서에서 시간표 데이터를 반환"""
    syllabus_url = (
        f"https://ecampus.smu.ac.kr/local/ubion/setting/syllabus.php?id={course_id}"
    )
    driver.get(syllabus_url)

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "lxml")

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

    # 강의 시간 파싱 (시간표용 데이터 준비)
    schedules = []
    if course_time != "정보 없음":
        time_slots = course_time.split()
        for slot in time_slots:
            match = re.match(
                r"([월화수목금토일])(?:\s*)(\d+(?:,\d+)*|-?\d+(?:-\d+)?|\d+)\((.+?)\)",
                slot,
            )
            if match:
                day, periods_part, location = match.groups()
                if "," in periods_part:
                    periods = [int(p) for p in periods_part.split(",")]
                elif "-" in periods_part:
                    start, end = map(int, periods_part.split("-"))
                    periods = list(range(start, end + 1))
                else:
                    periods = [int(periods_part)]
                for period in periods:
                    start_hour = period + 8
                    end_hour = start_hour + 1
                    time_range = f"{start_hour:02d}:00~{end_hour:02d}:00"
                    schedules.append((day, time_range, location))
            else:
                print(f"⚠️ 파싱 실패 - 강의 시간: {slot}")

    return course_name, course_time, schedules


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
                print(f"✅ 태그 저장: {tag.name}")

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
                print(
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
    time.sleep(2)

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
    time.sleep(2)
    print("➡️ 다음 달로 이동했습니다.")
