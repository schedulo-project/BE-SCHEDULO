# BE-SCHEDULO
Schedulo 백엔드 레포지토리

주요 기능: 사용자 인증 및 크롤링, 시간표 및 일정 관리, 알림 발송(FCM, Web Push), 챗봇 기능

---

## 📂 Project Structure
```bash
config/         # Django 설정
users/          # 사용자 기능 (로그인, 크롤링, 시간표)
schedules/      # 일정 관리
notifications/  # 알림 (FCM, Web Push)
chatbots/       # 챗봇 기능
logs/           # 애플리케이션 로그 저장
data/           # Celery Beat 스케줄 DB
```

---
## ⚙️ Local Development
```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. DB 마이그레이션
python manage.py migrate

# 4. Django 서버 실행
python manage.py runserver

# 5. Celery 워커 실행
celery -A config worker -l info

# 6. Celery 비트 실행
celery -A config beat -l info
```

---
## 📜 Commit Rules
    
Header 형식
```bash
type(scope): description
```
- scope: 앱 이름, 클래스, 함수명 (생략 가능)


예시:
```bash
fix(UserLoginAPIView): password 인코딩 수정
DB에 User의 password를 인코딩하지 않고 저장되는 오류 수정
```

Commit Type
- Header Type 종류
  - feat: 새로운 기능을 추가
  - fix: 버그 수정
  - chore : 자잘한 수정, 패키지 관련, 설정 관련 추가 및 변경
  - refactor: 코드 리팩토링

---
## Deployment
- WSGI: uWSGI
- Proxy: Nginx
- Process Manager: systemd


## Tech Stack
- **Framework**: Django REST Framework  
- **Database**: MySQL  
- **Task Queue**: Celery + Redis  
- **Crawling**: Selenium  
- **Notifications**: Firebase Cloud Messaging (FCM), Web Push  
- **Chatbot**: LangChain, Gemini
- **Deployment**: Nginx + uWSGI, systemd, Ubuntu, AWS(EC2, RDS)

## Service Architecture


