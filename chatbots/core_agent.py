import os
import re
import json
import requests
from dotenv import load_dotenv
from django.utils import timezone
from django.forms.models import model_to_dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from users.models import *
from users.serializers import *
from schedules.models import *
from schedules.serializers import *
from schedules.views import tag_colors
from rest_framework_simplejwt import tokens
from datetime import datetime

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LOCAL_URL = os.getenv("LOCAL_URL")
DOMAIN_URL = os.getenv("LOCAL_URL")

# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=GOOGLE_API_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY)


# User
def get_user_info(user_id):
    """
    사용자 정보를 조회하는 함수입니다. 사용자 id를 받아 해당 사용자의 정보를 반환합니다.
    """
    user = User.objects.get(id=user_id)
    serializer = UserSerializer(user)

    return {"message": "확인된 사용자 정보입니다. ", "data": serializer.data}


def get_user_studyroutine(user_id):
    """
    사용자 학습 루틴 정보를 조회하는 함수입니다. 사용자 id를 받아 해당 사용자의 학습 루틴 정보를 반환합니다.
    """
    user = User.objects.get(id=user_id)
    serializer = StudyRoutineSerializer(user.studyroutine)

    return {"message": "확인된 사용자 학습 루틴 정보입니다. ", "data": serializer.data}


def get_user_score(user_id):
    """
    사용자 점수 정보를 조회하는 함수입니다. 사용자 id를 받아 해당 사용자의 점수 정보를 반환합니다.
    가장 최근 점수 정보가 현재 점수입니다.
    """
    user = User.objects.get(id=user_id)
    scores = Score.objects.filter(user=user).order_by("-date")
    scores_dict = [model_to_dict(score) for score in scores]

    return {"message": "확인된 사용자 점수 정보입니다. ", "data": scores_dict}


USERS_TOOLS = [get_user_info, get_user_studyroutine, get_user_score]


# Schedule
def create_schedule(
    user_id, title, scheduled_date, tags=None, deadline=None, is_completed=False
):
    """
    일정을 생성하는 함수 입니다. 사용자 id를 받아 해당 사용자의 일정을 생성합니다.
    title: 일정의 제목, scheduled_date: 일정 날짜, deadline: 마감 날짜,
    날짜 변수들은 YYYY-MM-DD 형식의 문자열,
    tags: 태그 리스트(["태그이름1", "태그이름2",..]), is_completed: 완료 여부
    user_id, title, scheduled_date은 필수
    """
    user = User.objects.get(id=user_id)
    schedule = Schedule.objects.create(
        title=title,
        scheduled_date=scheduled_date,
        deadline=deadline,
        is_completed=is_completed,
        user=user,
    )
    if tags:
        tag_instances = []
        for tag_name in tags:
            tag_instance, created = Tag.objects.get_or_create(name=tag_name, user=user)
            if created:
                order = Tag.objects.filter(user=user).count()
                tag_instance.color = tag_colors[order % len(tag_colors)]
                tag_instance.save()
            tag_instances.append(tag_instance)
        schedule.tag.set(tag_instances)

    serializer = ScheduleSerializer(schedule)

    return {"message": "일정이 생성되었습니다. ", "data": serializer.data}


def list_schedules(user_id, scheduled_date, deadline=None):
    """
    일정 목록을 조회 함수
    사용자 id를 받아 해당 사용자의 일정 목록 반환
    scheduled_date: 일정 날짜, deadline: 마감 날짜, 날짜 변수들은 YYYY-MM-DD 형식의 문자열
    user_id, scheduled_date은 필수
    scheduled_date가 명시되지 않은 경우 모든 일정의 양이 너무 많기 때문에 시간이 오래 걸림을 안내 후 사용자에게 날짜 명시를 요구하되,
    그럼에도 전체 일정 조회를 요구한다면 그냥 실행하세요.
    하루 일정만 조회하고 싶은 경우 deadline을 생략, 여러 날짜의 일정을 조회하고 싶을 때 deadline을 지정
    "1일, 3일, 10일 일정 조회해줘"와 같은 요청은 본 함수를 세 번 호출한 후 결과를 취합
    """
    user = User.objects.get(id=user_id)
    scheduled_date_instance = datetime.strptime(scheduled_date, "%Y-%m-%d").date()

    if deadline is not None:
        deadline_instance = datetime.strptime(deadline, "%Y-%m-%d").date()
        schedules = Schedule.objects.filter(
            user=user,
            scheduled_date__range=[scheduled_date_instance, deadline_instance],
        )
    elif scheduled_date and not deadline:
        schedules = Schedule.objects.filter(
            user=user, scheduled_date=scheduled_date_instance
        )

    if not schedules.exists():
        return None

    serializer = GroupedScheduleSerializer(schedules)

    return {"message": "확인된 일정 목록입니다. ", "data": serializer.data}


def update_schedule(
    user_id, schedule_id, title, scheduled_date, tags, deadline, is_completed
):
    """
    일정을 수정하는 함수 입니다.
    사용자 id와 일정 id를 받아 해당 일정이 사용자의 일정인지 확인한 후 수정합니다.
    title은 일정의 제목, scheduled_date는 일정 날짜, deadline은 마감 날짜,
    날짜 변수들은 YYYY-MM-DD 형식의 문자열,
    tags는 태그 리스트(["태그이름1", "태그이름2",..]), is_completed는 완료 여부입니다.
    모든 매개변수 값이 필수이며, 수정하지 않을 부분은 기존 Schedule의 원본 값을 넘겨주어야 합니다.
    """
    user = User.objects.get(id=user_id)
    schedule = Schedule.objects.get(id=schedule_id, user=user)

    schedule.title = title
    schedule.scheduled_date = scheduled_date
    schedule.deadline = deadline
    schedule.is_completed = is_completed
    schedule.save()

    tag_instances = []
    for tag_name in tags:
        tag_instance, created = Tag.objects.get_or_create(name=tag_name, user=user)
        if created:
            order = Tag.objects.filter(user=user).count()
            tag_instance.color = tag_colors[order % len(tag_colors)]
            tag_instance.save()
        user = (user,)

    tag_instances = []
    for tag_name in tags:
        tag_instance, created = Tag.objects.get_or_create(name=tag_name, user=user)
        if created:
            order = Tag.objects.filter(user=user).count()
            tag_instance.color = tag_colors[order % len(tag_colors)]
            tag_instance.save()
        tag_instances.append(tag_instance)
    schedule.tag.set(tag_instances)

    serializer = ScheduleSerializer(schedule)

    return {"message": "일정이 수정되었습니다. ", "data": serializer.data}


def delete_schedules(schedule_id):
    """
    일정을 삭제하는 함수입니다. 일정 id를 받아 해당 일정을 삭제합니다.
    """
    schedule = Schedule.objects.get(id=schedule_id)
    schedule.delete()

    return {"message": "일정이 삭제되었습니다. "}


def import_schedules(user_id):
    """
    크롤링 API를 호출하여 사용자의 일정을 가져오는 함수입니다.
    """
    token = tokens.AccessToken.for_user(User.objects.get(id=user_id))

    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(DOMAIN_URL + "crawling/", headers=headers)

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
    response = requests.post(DOMAIN_URL + "tags/", headers=headers, data={"name": name})

    return {"message": "태그가 생성되었습니다. ", "data": response.json()}


def list_tag(user_id):
    """
    태그 목록을 조회하는 함수 입니다. 사용자 id를 받아 해당 사용자의 태그 목록을 반환합니다."""
    user = User.objects.get(id=user_id)
    tags = Tag.objects.filter(user=user)
    serializer = TagSerializer(tags, many=True)

    return {"message": "확인된 태그 목록입니다. ", "data": serializer.data}


def update_tag(user_id, tag_id, name):
    """
    태그 이름을 수정하는 함수입니다.
    사용자 id와 태그 id를 받아 해당 태그가 사용자의 태그인지 확인한 후 이름을 수정합니다.
    """
    token = tokens.AccessToken.for_user(User.objects.get(id=user_id))

    headers = {
        "Authorization": f"Bearer {token}",
    }
    response = requests.put(
        DOMAIN_URL + f"tags/{tag_id}/", headers=headers, data={"name": name}
    )

    return {"message": "태그 이름이 수정되었습니다. ", "data": response.json()}


def delete_tag(tag_id):
    """
    태그를 삭제하는 함수입니다. Tag id를 받아 해당 태그를 삭제합니다.
    """
    Tag.objects.get(id=tag_id).delete()

    return {"message": "태그가 삭제되었습니다. "}


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


def list_timetable(user_id):
    """
    시간표를 조회하는 함수 입니다. 사용자 id를 받아 해당 사용자의 시간표 목록을 반환합니다.
    """
    user = User.objects.get(id=user_id)
    timetables = TimeTable.objects.filter(user=user)
    serializer = TimeTableSerializer(timetables, many=True)

    return {"message": "확인된 시간표 목록입니다. ", "data": serializer.data}


def update_timetable(user_id, timetable_id, subject, day_of_week, start_time, end_time):
    """
    시간표를 수정하는 함수입니다. 사용자 id와 시간표 id를 받아 수정합니다.
    모든 매개변수 값이 필수 수정하지 않는 부분은 원본 값을 넘겨줘야함
    """
    user = User.objects.get(id=user_id)
    timetable = TimeTable.objects.get(id=timetable_id, user=user)
    timetable.subject = subject
    timetable.day_of_week = day_of_week
    timetable.start_time = start_time
    timetable.end_time = end_time
    timetable.save()

    serializer = TimeTableSerializer(timetable)

    return {"message": "수정된 시간표입니다. ", "data": serializer.data}


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
    response = requests.get(DOMAIN_URL + "timetable/status/", headers=headers)

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


PAGE_STRUCTURE = """
- 홈 페이지 (버튼 위치: 좌측 상단 "달력" 버튼)
    - 페이지 구성
    - 월별, 주별 캘린더 (일정 시각화)
    - 할 일 목록 (특정 날짜의 일정)
    - 일정 CRUD, 완료 처리 (제목, 내용, 태그, 날짜나 기간을 정하여 일정을 등록하고 일정을 관리)
    - 일정 연동 (샘물 포털만 가능, 시간표에 따른 일정 가져옴)
- 태그별 일정 조회 페이지 (일정을 태그별로 조회 가능) (버튼 위치: "달력" 버튼 아래의 "태그" 버튼)
- 포커스 타이머 (할 일에 집중할 수 있도록 타이머 기능 제공) (버튼 위치: "태그" 버튼 아래의 "포커스타이머" 버튼)
- 시간표 (직접 입력 혹은 샘물 포털 연동 가능) (버튼 위치: "포커스타이머" 버튼 아래의 "시간표" 버튼)
- 설정 (버튼 위치: "시간표" 버튼 아래의 "설정" 버튼)
    - 프로필
        - 개인정보 수정 (비밀번호 수정, 샘물 정보 수정, 회원 탈퇴)
        - 알림 설정 (아침, 저녁마다 오늘의 일정에 대한 알림을 보내주는 기능에 대한 On/Off)
        - 공부 계획 수정 (자신만의 시험 기간 - 시험 공부 일정 생성에 사용, 복습 주기 - 복습 주기와 시간표에 따라 복습 일정 자동)
    - 통계 및 시각화 (일정 완료율에 대한 점수 및 순위 제공)
- 시험 공부 일정 생성 (시험 기간과 과목, 공부량, 과목별 공부 비율 등을 입력하면 시험 공부 일정 자동 생성) (버튼 위치: "설정" 버튼 아래의 "시험 계획 설정" 버튼)
- 로그아웃 (버튼 위치: 좌측 최하단의 로그아웃 버튼)
"""

CORE_AGENT = create_react_agent(
    model=llm,
    tools=USERS_TOOLS + SCHEDULES_TOOLS + TAGS_TOOLS + TIMETABLE_TOOLS,
    prompt=f"""
    당신은 대학생의 학습 일정을 관리하는 서비스의 비서 Dulo 입니다. 
    당신은 사용자의 요청을 분석하여 적절한 툴을 호출하고 적절한 응답과 API의 결과를 전달합니다.  
    경우에 따라 툴을 순차적으로 사용하거나 툴 사용의 결과값을 분석해서 응답하세요.
    - 이번주 일정 뭐야? 등의 경우에는 이번주에 해당하는 월요일부터 일요일까지의 일정들을 모두 조회한 후 취합하세요. 단, 기존 API 데이터 반환 형태를 유지하며 취합하세요. 
    - 축구 일정 뭐야? 라는 질의에는 일정을 조회한 후 그 중 제목에 "축구"가 들어가거나, "축구" 태그가 붙은 일정들만 추출하여 보여주는 등 유연하게 대처하세요. 
    그럼에도 툴을 사용하여 처리할 수 없는 요청이나 사용자가 기능 실행이 아닌 페이지 위치 안내를 요구할 경우 {PAGE_STRUCTURE}를 참고하여 페이지 위치를 안내합니다.
    사용자 정보는 사용자 ID를 참고하고, 오늘 날짜는 {timezone.localtime(timezone.now()).strftime("%Y-%m-%d")} 입니다.
    오류나 예외 발생 시 발생 했음을 사용자에게 추가 요청을 요구하거나 해결 방법을 알립니다. 해결이 어려울 시 해당 사실을 솔직하게 말합니다.
    반환 형태: 
    {{
        "message": 사용자 요청에 대한 응답 (확인된 일정은 ~, ~입니다, 일정이 없습니다, 태그가 생성되었습니다... 등),
        "data": 사용자 요청에 대한 데이터(없을 경우 null),
        "render_html": data가 없거나 사용자에게 보일 필요가 없을 시 false, data가 있는데 사용자에게 시각적으로 보여줄 필요가 있을 때 true, true의 경우 HTML 렌더링 Agent가 호출됨,
        "template_name": schedules_list.html(날짜별 일정 목록 시각화에 사용되는 템플릿), tags_list.html(태그별 일정 목록 시각화에 사용되는 템플릿), timetables_list.html(시간표 목록 시각화에 사용되는 템플릿) 
            중 하나입니다. 사용자 질의와 data에 따라 적절히 선택하거나 null로 둘 수 있습니다. render_html이 false일 경우는 무조건 null 입니다.
    }}

    이러한 형태 이외의 답변을 **절대로 금지합니다.**
    """,
)


def run_core_agent(query: str, user_id: int):
    messages = [
        SystemMessage(content=f"사용자 ID: {user_id}"),
        HumanMessage(content=query),
    ]
    response = CORE_AGENT.invoke({"messages": messages})

    # 마지막 AIMessage 찾기
    ai_msg = next(
        (msg for msg in reversed(response["messages"]) if isinstance(msg, AIMessage)),
        None,
    )

    if ai_msg is None:
        return {
            "message": "AI 응답 없음",
            "data": None,
            "render_html": False,
            "template_name": False,
        }
    print(ai_msg)
    # ```json ... ``` 코드블록 제거
    content = ai_msg.content
    print(1)
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    print(2)
    if match:
        content = match.group(1)

    # JSON 디코딩
    try:
        content_dict = json.loads(content)
    except json.JSONDecodeError:
        content_dict = {
            "query": query,
            "message": ai_msg.content,
            "data": None,
            "render_html": False,
            "template_name": False,
        }

    return content_dict
