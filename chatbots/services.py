import json
import os
import google.generativeai as genai
from django.utils.timezone import now
from dotenv import load_dotenv

# API 키 로드
load_dotenv()

API_KEY = os.getenv("GEMIINI_API_KEY")

genai.configure(api_key=API_KEY)

MODEL = genai.GenerativeModel("gemini-2.0-flash")
PROMPT = f"""
사용자의 요청을 분석하여 필요한 정보를 JSON 형식으로 추출하세요.

규칙:
- 'tag'는 사용자 요청의 종류를 나타내며 일정의 종류, 과목명 등이 될 수 있습니다. 사용자가 명시하지 않을 시 '전체'로 설정합니다.
- 'date'는 YYYY-MM-DD 형식이며, 특정 날짜가 명시되지 않으면 'unknown'으로 설정합니다. 만약 이번주, 이번달 등이 명시되면 해당 기간을 YYYY-MM-DD~YYYY-MM-DD 형식으로 설정하세요.
- 'method'은 사용자의 요청 의도를 나타내며, ['조회', '등록', '삭제', '수정'] 중 하나여야 합니다. 사용자의 요청 의도를 파악하기 어려울 시 'unknown'으로 설정하세요.
- 'details'에는 사용자가 지정한 특정 작업을 설정하세요. 단, 'method'가 '조회'일 때는 'unknown'으로 설정하세요. 사용자가 지정한 작업 중 핵심이 되는 단어만 추출하여 설정하세요.
- 사용자가 지난 실행을 취소하려 한다면 'method'를 '취소'로 설정하세요.

조회 예제 출력:
사용자: "내일 일정 알려줘"
응답: {{"tag": "전체", "date": "2025-03-23", "method": "조회", "details": "unknown"}}

사용자: "이번 주 공부 일정 알려줘"
응답: {{"tag": "공부", "date": "2025-03-17~2025-03-23", "method": "조회", "details": "unknown"}}


등록 예제 출력:
사용자: "3월 21일 시스템프로그래밍 과제 일정 추가"
응답: {{"tag": "시스템프로그래밍", "date": "2025-03-21", "method": "등록", "details": "과제"}}

사용자: "다음주 시스템프로그래밍 과제 일정 추가"
응답: {{"tag": "시스템프로그래밍", "date": "2025-03-21", "method": "등록", "details": "과제"}}

수정 예제 출력(수정의 경우 직접 수정을 수행하지 않기 때문에 원래 일정만 출력합니다. ):
사용자: "내일 있는 축구하기 일정 야구하기로 수정해줘"
응답: {{"tag": "시스템프로그래밍", "date": "2025-03-20", "method": "수정", "details": "축구"}}

삭제 예제 출력:
사용자: "내일 있는 축구하기 일정 삭제해줘"
응답: {{"tag": "시스템프로그래밍", "date": "2025-03-20", "method": "삭제", "details": "축구"}}

지금부터 이 입력에 대한 JSON을 생성하세요:
"""


def get_chatbot_response(message: str):
    today = str(now())[:10]
    date_info = f"오늘의 날짜는 {today}입니다. 참고하세요. "
    response = MODEL.generate_content(date_info + PROMPT + message)
    return response.text if response else None
