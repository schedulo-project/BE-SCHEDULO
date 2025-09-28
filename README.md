# BE-SCHEDULO
Schedulo 백엔드 레포지토리

주요 기능: 사용자 인증 및 크롤링, 시간표 및 일정 관리, 알림 발송, 챗봇

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
## 🛠️ System Architecture
### ALL
<img width="538" height="253" alt="Image" src="https://github.com/user-attachments/assets/f7071dc8-3196-4066-9de2-bc9dac8b07e8" />

### Backend
<img width="378" height="209" alt="Image" src="https://github.com/user-attachments/assets/b20e8593-9916-40c8-aba8-1207ef76b6d0" />

### Extra
<img width="536" height="123" alt="Image" src="https://github.com/user-attachments/assets/8b53efab-500b-49f3-9618-44460883daff" />


### AI Agent Chatbot
<img width="515" height="205" alt="Image" src="https://github.com/user-attachments/assets/b2a302bc-c315-4efb-9dec-ca9ab6b1ca95" />


---
## 🚀 Detail Backend Tech Stack

<table> <thead> <tr> <th>분류</th> <th>기술 스택</th> </tr> </thead> <tbody> <tr> <td>Framework</td> <td> <img src="https://img.shields.io/badge/Django REST Framework-092E20?style=flat&logo=django&logoColor=white"/> </td> </tr> <tr> <td>Database</td> <td> <img src="https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white"/> </td> </tr> <tr> <td>Task Queue</td> <td> <img src="https://img.shields.io/badge/Celery-37814A?style=flat&logo=celery&logoColor=white"/> <img src="https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white"/> </td> </tr> <tr> <td>Crawling</td> <td> <img src="https://img.shields.io/badge/Selenium-43B02A?style=flat&logo=selenium&logoColor=white"/> </td> </tr> <tr> <td>Notifications</td> <td> <img src="https://img.shields.io/badge/Firebase Cloud Messaging-FFCA28?style=flat&logo=firebase&logoColor=black"/> <img src="https://img.shields.io/badge/Web Push-4285F4?style=flat&logo=googlechrome&logoColor=white"/> </td> </tr> <tr> <td>Chatbot</td> <td> <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat&logo=python&logoColor=white"/> <img src="https://img.shields.io/badge/Gemini-4285F4?style=flat&logo=google&logoColor=white"/> </td> </tr> <tr> <td>Deployment</td> <td> <img src="https://img.shields.io/badge/Nginx-009639?style=flat&logo=nginx&logoColor=white"/> <img src="https://img.shields.io/badge/uWSGI-222222?style=flat&logo=python&logoColor=white"/> <img src="https://img.shields.io/badge/systemd-5A29E4?style=flat&logo=linux&logoColor=white"/> <img src="https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white"/> <img src="https://img.shields.io/badge/AWS EC2-FF9900?style=flat&logo=amazonec2&logoColor=white"/> <img src="https://img.shields.io/badge/AWS RDS-527FFF?style=flat&logo=amazonrds&logoColor=white"/> </td> </tr> </tbody> </table>

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


## 👥 팀원 소개

| 이름   | 역할 | GitHub |
| ------ | ---- | ------ |
| 주현지 | Backend, Crawling, Notifications, User | [@zoohj](https://github.com/zoohj) |
| 백승우 | Backend, AI Agent, Electron, Schedule  | [@s2vngwxx](https://github.com/s2vngwxx) |

