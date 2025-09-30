import os
import re
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from django.utils import timezone
from rest_framework_simplejwt import tokens

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from users.models import *
from users.serializers import *
from schedules.models import *
from schedules.serializers import *
from schedules.views import tag_colors
from chatbots.models import Chatting
from chatbots.serializers import ChattingSerializer


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LOCAL_URL = os.getenv("LOCAL_URL")
DOMAIN_URL = os.getenv("DOMAIN_URL")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY)


# User
def get_user_info(user_id: int):
    """
    사용자 정보를 조회하는 함수입니다.
    """
    user = User.objects.filter(id=user_id).values("email", "student_id").first()

    if not user:
        return {"message": "사용자를 찾을 수 없습니다.", "data": None}

    return {"message": "확인된 사용자 정보입니다.", "data": user}


def get_user_studyroutine(user_id: int):
    """
    사용자 학습 루틴 정보를 조회하는 함수입니다.
    반환 값 중 weeks_before_exam은 시험 기간을 시험 몇 주 전으로 여기는지에 대한 정보입니다.
    review_type은 사용자의 복습 타입으로 "SAMEDAY"일 경우 학습 당일 복습, 그 외 "MON", "TUE", "WED" 등 요일의 영어명의 앞 세 글자의 조합으로 된 경우, 해당 요일에 복습을 하는 타입입니다.
    """
    user = User.objects.filter(id=user_id).first()
    if not user:
        return {"message": "학습 루틴 정보를 찾을 수 없습니다.", "data": None}

    routines = user.study_routine.all()
    routine = routines.first()

    if not routine:
        return {"message": "학습 루틴 정보를 찾을 수 없습니다.", "data": None}

    routine = routines.first()

    routine_data = {
        "시험 기간": f"시험 시작 {routine.weeks_before_exam}주 전",
        "복습 유형": routine.review_type,
    }

    return {"message": "확인된 사용자 학습 루틴 정보입니다.", "data": routine_data}


def get_user_score(user_id: int):
    """
    사용자 점수 정보를 조회하는 함수입니다.
    가장 최근 점수 정보가 현재 점수입니다.
    """
    scores = (
        Score.objects.filter(user_id=user_id)
        .order_by("-date")
        .values("score", "date", "highest", "percentage")
    )

    return {"message": "확인된 사용자 점수 정보입니다.", "data": list(scores)}


USERS_TOOLS = [get_user_info, get_user_studyroutine, get_user_score]


# Schedule
from django.shortcuts import get_object_or_404
from django.db import transaction


def create_schedule(
    user_id,
    title,
    scheduled_date,
    content=None,
    tags=None,
    deadline=None,
    is_completed=False,
):
    """
    일정을 생성하는 함수 입니다. 사용자 id를 받아 해당 사용자의 일정을 생성합니다.
    title: 일정의 제목, content: 일정의 내용, scheduled_date: 일정 날짜, deadline: 마감 날짜,
    날짜 변수들은 YYYY-MM-DD 형식의 문자열,
    tags: 태그 리스트(["태그이름1", "태그이름2",..]), is_completed: 완료 여부
    user_id, title, scheduled_date은 필수
    """
    user = get_object_or_404(User.objects.only("id"), id=user_id)

    with transaction.atomic():
        schedule = Schedule.objects.create(
            title=title,
            content=content,
            scheduled_date=scheduled_date,
            deadline=deadline,
            is_completed=is_completed,
            user=user,
        )

        if tags:
            existing_tags = Tag.objects.filter(user=user, name__in=tags)
            existing_names = set(existing_tags.values_list("name", flat=True))

            new_names = [name for name in tags if name not in existing_names]

            created_tags = []
            if new_names:
                current_count = Tag.objects.filter(user=user).count()
                new_tags = [
                    Tag(
                        user=user,
                        name=name,
                        color=tag_colors[(current_count + idx) % len(tag_colors)],
                    )
                    for idx, name in enumerate(new_names)
                ]
                created_tags = Tag.objects.bulk_create(new_tags)

            all_tags = list(existing_tags) + created_tags
            schedule.tag.set(all_tags)

    return {
        "message": "일정이 생성되었습니다.",
        "data": ScheduleSerializer(schedule).data,
    }


def list_schedules(user_id, scheduled_date, deadline=None, tag_name=None):
    """
    일정 목록을 조회 함수
    사용자 id를 받아 해당 사용자의 일정 목록 반환
    scheduled_date: 일정 날짜, deadline: 마감 날짜, 날짜 변수들은 YYYY-MM-DD 형식의 문자열
    user_id, scheduled_date은 필수
    scheduled_date가 명시되지 않은 경우 사용자에게 날짜 명시를 요구하세요.
    하루 일정만 조회하고 싶은 경우 deadline을 생략, 여러 날짜의 일정을 조회하고 싶을 때 deadline을 지정
    "1일, 3일, 10일 일정 조회해줘"와 같은 요청은 본 함수를 세 번 호출한 후 결과를 취합
    """
    user = get_object_or_404(User.objects.only("id"), id=user_id)

    scheduled_date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()

    schedules_qs = Schedule.objects.filter(user=user)

    if deadline:
        deadline_obj = datetime.strptime(deadline, "%Y-%m-%d").date()
        schedules_qs = schedules_qs.filter(
            scheduled_date__range=[scheduled_date_obj, deadline_obj]
        )
    else:
        schedules_qs = schedules_qs.filter(scheduled_date=scheduled_date_obj)

    if tag_name:
        schedules_qs = schedules_qs.filter(tag__name=tag_name)

    schedules_qs = schedules_qs.select_related("user").prefetch_related("tag")

    if not schedules_qs.exists():
        return None

    return {
        "message": "확인된 일정 목록입니다.",
        "data": ScheduleSerializer(schedules_qs, many=True).data,
    }


def update_schedule(
    user_id,
    schedule_id,
    title=None,
    content=None,
    scheduled_date=None,
    tags=None,
    deadline=None,
    is_completed=None,
):
    """
    일정을 수정하는 함수 입니다.
    사용자 id와 일정 id를 받아 해당 일정이 사용자의 일정인지 확인한 후 수정합니다.
    title: 일정의 제목, content: 일정의 내용, scheduled_date: 일정 날짜, deadline: 마감 날짜,
    날짜 변수들은 YYYY-MM-DD 형식의 문자열,
    tags는 태그 리스트(["태그이름1", "태그이름2",..]), is_completed는 완료 여부입니다.
    tags가 있다면, 일정의 기존 태그들은 모두 사라지고 tags로 바뀝니다. 기존 태그는 schedule_id로 일정을 조회하고 태그 데이터를 확인하여 사용하세요.
    - 예시: 태그1과는 이미 연결되어있는데 태그2를 추가하고 싶다 -> 일정 조회 후 태그값 조회하여 태그1과 연결된 것 확인 -> tags=["태그1","태그2"] 매개변수 전달, 삭제도 마찬가지
    """
    user = get_object_or_404(User.objects.only("id"), id=user_id)
    schedule = get_object_or_404(
        Schedule.objects.select_related("user"), id=schedule_id, user=user
    )

    with transaction.atomic():
        if title is not None:
            schedule.title = title
        if content is not None:
            schedule.content = content
        if scheduled_date is not None:
            schedule.scheduled_date = scheduled_date
        if deadline is not None:
            schedule.deadline = deadline
        if is_completed is not None:
            schedule.is_completed = is_completed

        schedule.save()
        if tags:
            existing_tags = Tag.objects.filter(user=user, name__in=tags)
            existing_names = set(existing_tags.values_list("name", flat=True))
            new_names = [name for name in tags if name not in existing_names]

            created_tags = []
            if new_names:
                current_count = Tag.objects.filter(user=user).count()
                new_tags = [
                    Tag(
                        user=user,
                        name=name,
                        color=tag_colors[(current_count + idx) % len(tag_colors)],
                    )
                    for idx, name in enumerate(new_names)
                ]
                created_tags = Tag.objects.bulk_create(new_tags)

            all_tags = list(existing_tags) + created_tags
            schedule.tag.set(all_tags)

    return {
        "message": "일정이 수정되었습니다.",
        "data": ScheduleSerializer(schedule).data,
    }


def delete_schedules(schedule_id):
    """
    일정을 삭제하는 함수입니다. 일정 id를 받아 해당 일정을 삭제합니다.
    """
    Schedule.objects.get(id=schedule_id).delete()

    return {"message": "일정이 삭제되었습니다. "}


def import_schedules(user_id):
    """
    크롤링 API를 호출하여 학사 시스템 일정을 가져오는 함수입니다.
    """
    token = tokens.AccessToken.for_user(User.objects.get(id=user_id))

    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(DOMAIN_URL + "users/crawling/", headers=headers)

    return {"message": "학사 시스템 연동이 실행되었습니다. ", "data": response.json()}


SCHEDULES_TOOLS = [
    create_schedule,
    list_schedules,
    update_schedule,
    delete_schedules,
    import_schedules,
]


# Tag
def create_tag(user_id, name):
    """
    사용자 id와 태그 이름을 받아 태그를 생성하거나 이미 존재하는 태그일 경우 이를 반환하는 함수입니다.
    """
    token = tokens.AccessToken.for_user(User.objects.get(id=user_id))

    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.post(
        DOMAIN_URL + "schedules/tags/", headers=headers, data={"name": name}
    )

    return {"message": "태그가 생성되었습니다. ", "data": response.json()}


def list_tag(user_id):
    """
    태그 목록을 조회하는 함수입니다.
    """
    user = get_object_or_404(User.objects.only("id"), id=user_id)
    tags = Tag.objects.filter(user=user).only("id", "name", "color")

    return {
        "message": "확인된 태그 목록입니다.",
        "data": TagSerializer(tags, many=True).data,
    }


def update_tag(user_id, tag_id, name):
    """
    태그 이름을 수정하는 함수입니다.
    """
    user = get_object_or_404(User.objects.only("id"), id=user_id)
    tag = get_object_or_404(Tag.objects.select_for_update(), id=tag_id, user=user)

    with transaction.atomic():
        tag.name = name
        tag.save(update_fields=["name"])

    return {
        "message": "태그 이름이 수정되었습니다.",
        "data": TagSerializer(tag).data,
    }


def delete_tag(tag_id):
    """
    태그를 삭제하는 함수입니다.
    """
    Tag.objects.filter(id=tag_id).delete()
    return {"message": "태그가 삭제되었습니다."}


TAGS_TOOLS = [create_tag, list_tag, update_tag, delete_tag]


# Timer
def timer_tools():
    pass


# TimeTable
def create_timetable(user_id, subject, day_of_week, start_time, end_time):
    """
    시간표를 생성하는 함수 입니다. 사용자 id를 받아 해당 사용자의 시간표를 생성합니다.
    subject: 과목명, day_of_week: 요일(mon, tue, .., sun),
    start_time: 시작 시간, end_time: 종료 시간 - HH:MM 형식의 문자열
    모든 매개변수가 필수값
    같은 시간에 겹치는 시간이 있을 경우 이를 알려주고 생성하지 않음
    중복 여부는 시간표 조회 사용
    과목명은 중복될 수 있음, 과목명이 같으면 같은 수업으로 간주
    """
    user = User.objects.get(id=user_id)
    timetable = TimeTable.objects.create(
        user=user,
        subject=subject,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    timetable.save()

    serializer = TimeTableSerializer(timetable)

    return {"message": "생성된 시간표입니다. ", "data": serializer.data}


DAY_MAP = {"sun": 1, "mon": 2, "tue": 3, "wed": 4, "thu": 5, "fri": 6, "sat": 7}
COLOR_LIST = [
    "bg-[#E6FEFF] border-[#24B0C9] text-[#24B0C9]",
    "bg-[#FFBABE] border-[#FF3C6A] text-[#FF3C6A]",
    "bg-[#FFDDBA] border-[#FF7A3C] text-[#FF7A3C]",
    "bg-[#FFE7BA] border-[#D78D03] text-[#D78D03]",
    "bg-[#E9EFFF] border-[#5272E9] text-[#5272E9]",
]


def time_to_float(t: str) -> float:
    h, m, s = map(int, t.split(":"))
    return h + m / 60


def transform_timetables(raw_data):
    color_map = {}
    transformed = []

    for item in raw_data:
        name = item["subject"]
        if name not in color_map:
            color_map[name] = COLOR_LIST[len(color_map) % len(COLOR_LIST)]

        transformed.append(
            {
                "name": name,
                "col": DAY_MAP.get(item["day_of_week"].lower(), 0),
                "start_hour": time_to_float(item["start_time"]),
                "end_hour": time_to_float(item["end_time"]),
                "color": color_map[name],
            }
        )

    return transformed


def list_timetable(user_id):
    """
    사용자 id를 받아 해당 사용자의 시간표 목록을 반환.
    Core Agent에서 바로 Render용 데이터 형태로 반환.
    """
    user = User.objects.get(id=user_id)
    timetables = TimeTable.objects.filter(user=user)
    serializer = TimeTableSerializer(timetables, many=True)

    transformed = transform_timetables(serializer.data)

    return {
        "message": "회원님의 시간표 목록입니다.",
        "data": {"timetables": transformed},
        "render_html": True,
        "template_name": "timetables_list.html",
    }


def update_timetable(user_id, timetable_id, subject, day_of_week, start_time, end_time):
    """
    시간표를 수정하는 함수입니다.
    사용자 id와 시간표 id를 받아 수정합니다.
    """
    timetable = get_object_or_404(
        TimeTable.objects.select_for_update(), id=timetable_id, user_id=user_id
    )

    with transaction.atomic():
        if subject is not None:
            timetable.subject = subject
        if subject is not None:
            timetable.day_of_week = day_of_week
        if start_time is not None:
            timetable.start_time = start_time
        if end_time is not None:
            timetable.end_time = end_time

        timetable.save()

    return {
        "message": "수정된 시간표입니다.",
        "data": TimeTableSerializer(timetable).data,
    }


def delete_timetable(timetable_id):
    """
    시간표를 삭제하는 함수입니다. 시간표 id를 받아 해당 시간표를 삭제합니다.
    """
    timetable = TimeTable.objects.get(id=timetable_id)
    timetable.delete()

    return {"message": "시간표가 삭제되었습니다. "}


def import_timetable(user_id):
    """
    크롤링 API를 호출하여 사용자의 시간표를 가져오는 함수입니다.
    비동기이므로 바로 시간표가 반영되지 않을 수 있습니다.
    """
    token = tokens.AccessToken.for_user(User.objects.get(id=user_id))

    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(DOMAIN_URL + "users/getTimeTable/", headers=headers)

    return {"message": "학사 시스템 연동이 실행되었습니다. ", "data": response.json()}


TIMETABLE_TOOLS = [
    create_timetable,
    list_timetable,
    update_timetable,
    delete_timetable,
    import_timetable,
]


# Setting
def settings_tools():
    pass


# 페이지 구조 (툴 불가 시 안내용)
PAGE_STRUCTURE = """
- 홈 페이지 (좌측 상단 "달력" 버튼)
    - 월별/주별 캘린더 (일정 시각화)
    - 할 일 목록 (특정 날짜 일정)
    - 일정 CRUD 및 완료 처리 (제목/내용/태그/기간 지정 가능)
    - 샘물 포털 연동 (시간표 기반 일정 가져오기)
- 태그별 일정 조회 (좌측 "태그" 버튼)
- 포커스 타이머 (좌측 "포커스타이머" 버튼)
- 시간표 (직접 입력 또는 샘물 연동, 좌측 "시간표" 버튼)
- 설정 (좌측 "설정" 버튼)
    - 프로필 관리 (비밀번호, 샘물 정보, 회원 탈퇴)
    - 알림 설정 (아침/저녁 일정 알림 On/Off)
    - 공부 계획 (시험 기간, 복습 주기)
    - 통계 (완료율, 순위 제공)
- 시험 공부 일정 자동 생성 (좌측 "시험 계획 설정" 버튼)
- 로그아웃 (좌측 하단 "로그아웃" 버튼)
"""

# 최적화된 SYSTEM_PROMPT
SYSTEM_PROMPT = f"""
너는 대학생 학습/일정 관리 비서 Dulo이다.
너의 아버지이자 개발자는 백승우다.
규칙:
- 사용자의 요청을 분석해 적절한 툴을 호출하고 필요 시 여러 툴을 순차적으로 사용한다.
- 일정 조회 시: 주간/태그/키워드 조건에 맞게 취합한다.
- 일정 응답은 날짜별로 묶어 {{"schedules": {{"날짜": [데이터...]}}}} 형식 사용.
- 시간표 응답은 그대로 data에 넣는다 (예: {{"timetables": [...]}}).
- 툴로 처리 불가하거나 위치 안내 요청일 경우 PAGE_STRUCTURE 참고.
- 출력은 JSON만 허용: {{
    "message": "사용자에게 보여줄 응답",
    "data": 툴 반환 데이터 or null,
    "render_html": true/false // data의 key가 schedules거나 timetables일 경우 true
  }}
- message에는 자연어 응답만, data에는 가공된 툴 응답만 넣는다.
- 오늘 날짜는 {timezone.localtime(timezone.now()).strftime("%Y-%m-%d")} 기준으로 처리한다.
- 최근 10개 대화 내역을 반드시 참고하여 맥락을 유지한다.
"""

USER_PROMPT_TEMPLATE = """
[사용자 요청]
{query}

[최근 대화 요약]
{history}
"""

# LLM 초기화
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY")
)

# CORE_AGENT 생성
CORE_AGENT = create_react_agent(
    model=llm,
    tools=USERS_TOOLS + SCHEDULES_TOOLS + TAGS_TOOLS + TIMETABLE_TOOLS,
    prompt=SYSTEM_PROMPT,
)


# 실행 함수
def run_core_agent(query: str, user_id: int):
    history = ChattingSerializer(
        Chatting.objects.order_by("-created_at")[:10], many=True
    ).data

    messages = [
        SystemMessage(content=f"사용자 ID: {user_id}"),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(query=query, history=history)),
    ]

    response = CORE_AGENT.invoke({"messages": messages})

    ai_msg = next(
        (msg for msg in reversed(response["messages"]) if isinstance(msg, AIMessage)),
        None,
    )

    if ai_msg is None:
        return {
            "query": query,
            "message": "AI 응답 없음",
            "data": None,
            "render_html": False,
        }

    content = ai_msg.content
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)

    try:
        content_dict = json.loads(content)
    except json.JSONDecodeError:
        content_dict = {
            "query": query,
            "message": ai_msg.content,
            "data": None,
            "render_html": False,
        }

    return content_dict
