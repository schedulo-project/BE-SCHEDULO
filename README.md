# BE-SCHEDULO
Schedulo 백엔드 레포지토리

## 프로젝트 구조
- `config/`: Django 설정 파일들
- `users/`: 사용자 관련 기능 (크롤링, 시간표 등)
- `schedules/`: 일정 관리 기능
- `notifications/`: 알림 기능
- `chatbots/`: 챗봇 기능
- `logs/`: 애플리케이션 로그 파일들이 저장되는 디렉토리
- `data/`: Celery Beat 스케줄 파일들이 저장되는 디렉토리

## Commit Rules
- **Header -> type(scope): description**, scope에는 앱 이름 or 클래스, 함수 이름 (생략 가능)
- e.g.
- fix(UserLoginAPIView): password 인코딩 수정
- DB에 User의 password를 인코딩 하지 않고 저장되는 오류 수정
- Issue #123
- Header Type 종류
  - feat: 새로운 기능을 추가
  - fix: 버그 수정
  - chore : 자잘한 수정, 패키지 관련, 설정 관련 추가 및 변경
