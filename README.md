# CatchData - 스마트 맛집 추천 플랫폼

## 목차

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [설치 및 실행](#-설치-및-실행)
- [프로젝트 구조](#-프로젝트-구조)

## 프로젝트 소개

CatchData는 사용자의 시간을 절약하고 최적의 식사 경험을 제공하기 위한 스마트 맛집 추천 플랫폼입니다.

### 핵심 가치

- **시간 효율성**: 실시간 대기 정보를 기반으로 빠른 입장이 가능한 맛집 추천
- **맞춤형 추천**: RAG 기반 AI 챗봇으로 사용자 상황에 맞는 개인화된 추천
- **데이터 기반 인사이트**: 대시보드를 통한 맛집 트렌드 및 통계 제공

## 주요 기능

### 1. AI 챗봇 맛집 추천 (RAG)
- **Google Gemini 2.5 Flash** 기반 자연어 처리
- **pgvector**를 활용한 벡터 검색으로 맥락 이해
- 대기 시간, 평점, 카테고리를 종합적으로 고려한 추천
- "10분의 미학" 철학: 대기 시간과 품질의 균형 추천

**추천 시나리오:**
```
사용자: "20분 후에 홍대에서 한식 먹고 싶어요"
AI: 대기 10분, 평점 4.8의 고품질 식당 vs 대기 0분, 평점 4.0 식당을
    상황에 맞게 추천
```

### 2. 대시보드 분석
- **카카오맵 API** 기반 지도 시각화
- 실시간 인기 레스토랑 TOP 5 (대기 인원 기반)
- 인기 카테고리 TOP 5
- 추천도 기준 TOP 5 (품질성/종합성/편의성)
- 카테고리 워드클라우드 (형태소 분석)
- 다차원 필터링 (지역/도시/카테고리)

### 3. 레스토랑 상세 정보
- 전화번호, 주소, 평점, 카테고리 등 상세 정보 제공
- **클러스터 기반 유사 맛집 추천** (rec_balanced 점수 기준)
- 원클릭 예약 기능

### 4. 채팅 기록 관리
- 모든 사용자 질의와 AI 응답을 RDS에 저장
- 사용자 행동 패턴 분석 가능

## 기술 스택

### Backend
- **Django 5.2.6** - Python 웹 프레임워크
- **Python 3.13** - 프로그래밍 언어
- **Gunicorn** - WSGI HTTP 서버

### Database
- **PostgreSQL (Amazon RDS)** - 메인 데이터베이스
- **pgvector** - 벡터 임베딩 저장 및 검색

### AI/ML
- **Google Gemini 2.5 Flash** - LLM 생성 모델
- **KoNLPy (Okt)** - 한국어 형태소 분석

### Frontend
- **HTML/CSS/JavaScript** - 기본 웹 기술
- **Kakao Maps JavaScript SDK** - 지도 시각화

### DevOps
- **AWS EC2** - 서버 호스팅
- **Nginx** - 리버스 프록시
- **GitHub Actions** - CI/CD (Ruff 코드 품질 체크)

## 시스템 아키텍처

### 프로젝트 아키텍쳐
<img width="2000" height="1600" alt="데이터flowdiagram drawio의 사본 drawio (1)" src="https://github.com/user-attachments/assets/e3e966bc-2d9a-40cf-aeda-d69a5d371c95" />


### 웹 서버
```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Nginx (Reverse Proxy)           │
└────────────────┬────────────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌─────────────┐    ┌──────────────┐
│  Gunicorn   │    │    Static    │
│   (WSGI)    │    │    Files     │
└──────┬──────┘    └──────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Django Application              │
├─────────────┬──────────────┬───────────┤
│    main     │  dashboard   │    RAG    │
│  (메인 앱)   │  (대시보드)   │ (AI 챗봇) │
└─────────────┴──────────────┴───────────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
       ┌──────────────┴──────────────┐
       ▼                             ▼
┌──────────────┐            ┌────────────────┐
│ PostgreSQL   │            │ Google Gemini  │
│   (RDS)      │            │   2.5 Flash    │
│ + pgvector   │            │      API       │
└──────────────┘            └────────────────┘
```

## 설치 및 실행

### 사전 요구사항
- Python 3.13+
- PostgreSQL (pgvector 확장 포함)
- Google Gemini API Key
- Kakao Maps API Key

### 1. 저장소 클론
```bash
git clone <repository-url>
cd CatchData-Django/FinalProject_Django
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정
`.env` 파일을 프로젝트 루트에 생성:
```env
# Django
SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=

# Database (Main)
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# Database (Vector)
VECTOR_DB_NAME=
VECTOR_DB_USER=
VECTOR_DB_PASSWORD=
VECTOR_DB_HOST=
VECTOR_DB_PORT=

# API Keys
GEMINI_API_KEY=
KAKAO_MAP_API_KEY=
```

### 5. 데이터베이스 마이그레이션
```bash
# 메인 데이터베이스
python manage.py makemigrations
python manage.py migrate

# 벡터 데이터베이스 (RAG)
python manage.py makemigrations RAG
python manage.py migrate RAG --database=vectordb
```

### 6. 임베딩 데이터 생성 (선택)
```bash
python manage.py embedding
```

### 7. 개발 서버 실행
```bash
python manage.py runserver
```

서버 실행 후 접속:
- 메인 페이지: 
- 대시보드: 

## 📁 프로젝트 구조

```
FinalProject_Django/
├── DE7FP_Django/           # Django 프로젝트 설정
│   ├── settings.py         # 설정 파일
│   ├── urls.py            # 루트 URL 설정
│   └── db_router.py       # 멀티 DB 라우터
│
├── main/                   # 메인 앱
│   ├── models.py          # Restaurant, ChatHistory 모델
│   ├── views.py           # LLM 챗봇, 레스토랑 상세 뷰
│   ├── urls.py            # URL 라우팅
│   └── templates/         # HTML 템플릿
│       ├── llm.html       # AI 챗봇 페이지
│       └── restaurant_detail.html
│
├── dashboard/              # 대시보드 앱
│   ├── models.py          # MapSearchHistory 모델
│   ├── views.py           # 통계, 필터링 API
│   ├── urls.py
│   └── templates/
│       └── dashboard.html # 대시보드 메인
│
├── RAG/                    # RAG AI 챗봇 앱
│   ├── models.py          # EmbeddedData 모델
│   ├── views.py           # RAG 챗봇 API
│   └── management/
│       └── commands/
│           └── embedding.py  # 임베딩 생성 커맨드
│
├── requirements.txt        # Python 의존성
├── .env                   # 환경변수 (git ignore)
├── .ruff.toml            # Ruff 린터 설정
└── README.md             # 프로젝트 문서
```


