import os
import re
import json
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from .templates import render_template

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LOCAL_URL = os.getenv("LOCAL_URL")
DOMAIN_URL = os.getenv("LOCAL_URL")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=GOOGLE_API_KEY)


# ----------------------------
# HTML Generator (LLM 모델)
# ----------------------------
def generate_html(query, data, template_name):
    system_prompt = """
    당신은 JSON 혹은 DICT 데이터의 구조를 변환하는 에이전트 입니다.
    일정 데이터 혹은 시간표 데이터가 넘어옵니다.

    주어진 데이터(data)를 아래의 설명을 읽고 변환하세요. 
    1. template_name이 "schedule_list.html"인 경우, 보통 일정 데이터가 넘어오고, 그대로 사용하면 됩니다.
    일정 데이터 형태:
    {{
        "schedules": {{
            "YYYY-MM-DD": [
            {{
                "id": int,
                "tag": [string],
                "title": string,
                "content": string,
                "deadline": string or null,
                "is_completed": bool,
                "order_num": int or null,
                "user": int
            }},
            ...
            ]
        }}
    }}

    2. template_name이 "tags_list.hthml"인 경우, 보통 일정 데이터가 넘어오고 당신은 아래 형식처럼 태그로 묶습니다. 
        일정은 태그를 여러개 가질 수 있기 때문에 서로 다른 태그에 같은 일정이 들어가는 것은 자연스럽습니다.
    변환 전 일정 데이터: 
    {{
        "schedules": {{
            "YYYY-MM-DD": [
            {{
                "id": int,
                "tag": [string],
                "title": string,
                "content": string,
                "deadline": string or null,
                "is_completed": bool,
                "order_num": int or null,
                "user": int
            }},
            ...
            ]
        }}
    }}

    변환 후 태그별 일정 데이터:
    tags: 일정 데이터의 모든 tag들로 원본 데이터의 name과 color를 그대로 사용하면 됨
    schedules: 태그와 연결된 일정 데이터로 원본 데이터의 title과 is_completed를 그대로 사용하면 됨
    {{
        "tags": [
            {{
                "name": "업무",
                "color": "#FF6B6B",
                "schedules": [
                    {{"title": "회의 준비", "is_completed": False}},
                    {{"title": "보고서 작성", "is_completed": True}},
                ]
            }},
            ...
        ]
    }}

    3. template_name이 "timetables_list.hthml"인 경우, 보통 시간표 데이터가 넘어오고 당신은 아래 형식으로 변환합니다. 
    원본 데이터:
    {{
        "timetables": [
            {{
                "day_of_week": "thu",
                "end_time": "15:00:00",
                "id": 1,
                "start_time": "12:00:00",
                "subject": "컴구",
                "user": 2
            }},
            ...
        ]
    }}
    변환해야할 포맷: 
    {{
        "timetables" : [
            name: 과목명으로 subject 값이 온다
            col: 날짜로 1~7의 값이며 day_of_week을 치환한 값이다(sun: 1, mon: 2, tue: 3, wed: 4, thu: 5, fir: 6, sat: 7)
            start_hour, end_hour: 시작 시간과 종료 시간으로 start_time, end_time을 치환한 값이다. (00:00: 0.0, 23:30: 23.5)
            colors: 색깔값으로 "bg-[#E6FEFF] border-[#24B0C9] text-[#24B0C9]", "bg-[#FFBABE] border-[#FF3C6A] text-[#FF3C6A]",
            "bg-[#FFDDBA] border-[#FF7A3C] text-[#FF7A3C]", "bg-[#FFE7BA] border-[#D78D03] text-[#D78D03]",
            "bg-[#E9EFFF] border-[#5272E9] text-[#5272E9]" 다섯 개 중 하나를 넣는다. 이름이 같다면 같은 색깔로 한다.
            {{
                "name": "컴구",
                "col": 3,
                "start_hour": 9.0,
                "end_hour": 10.0,
                "color": "bg-[#E6FEFF] border-[#24B0C9] text-[#24B0C9]",
            }},
            ...
        ]
    }}
    """
    human_prompt = f"""
    사용자 질의인 "{query}"에 대해 선행 에이전트가 "data = {data}", "template_name = {template_name}" 값을 넘겨줬는데 
    시스템 프롬프트와 이를 참고하여 변환 작업을 수행하세요.
    출력 형태는 다음과 같습니다.
    {{
        "html": 변환된 JSON(혹은 딕셔너리) 데이터, 만약 변환에 실패했다면 null을 반환
    }}
    **반드시 이를 준수하세요. **
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    response = llm.invoke(messages)
    content = response.content
    cleaned = re.sub(r"^```json\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
    print(cleaned)
    context = json.loads(cleaned)["html"]

    html = render_template(template_name, context).replace("\\n", "\n")

    return html
