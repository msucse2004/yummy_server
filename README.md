# Yummy Server

로컬 공장 PC에서 24/7 구동되는 배송/물류 관리 서버입니다.

## 스택

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- **인증**: 세션 기반 (HttpOnly 쿠키), RBAC (ADMIN / DRIVER)
- **Frontend**: PWA-capable 웹 (관리자/기사 화면 분리)

## 실행 방법

### 1. Docker Compose로 실행 (권장)

```bash
docker compose up -d
```

- **프론트엔드**: http://localhost:8080
- **DB**: localhost:5432 (PostgreSQL)
- **백엔드**: Docker 내부에서만 (프론트가 프록시)

### 2. 초기 Admin 계정 생성

컨테이너 기동 후, 마이그레이션이 자동 적용됩니다. admin 계정을 생성하려면:

```bash
docker compose exec backend python scripts/init_db.py
```

- **아이디**: admin
- **비밀번호**: admin123

### 3. 로컬 개발 (Docker 없이)

1. PostgreSQL 실행 후 DB 생성:
   ```bash
   createdb yummy
   ```

2. Backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   export DATABASE_URL=postgresql://yummy:yummy_secret@localhost:5432/yummy
   alembic upgrade head
   python scripts/init_db.py
   uvicorn app.main:app --reload --port 8000
   ```

3. Frontend (별도 터미널):
   - 정적 파일: `frontend/static/` 을 http-server 등으로 서빙
   - 또는 nginx로 `/api` 프록시 설정 후 `frontend/static` 서빙

## 외부 접속 (Cloudflare Tunnel)

서버는 외부에 포트를 열지 않아도 됩니다. Cloudflare Tunnel을 사용할 경우:

1. `cloudflared` 설치 및 터널 설정
2. 터널이 `localhost:8080` (프론트엔드)으로 연결
3. `COOKIE_DOMAIN`을 터널 도메인으로 설정
4. `COOKIE_SECURE=true` (HTTPS 사용 시)

## API 개요

| 구분 | 경로 | 설명 |
|------|------|------|
| 인증 | POST /api/auth/login | 로그인 |
| | GET /api/auth/me | 현재 사용자 |
| | POST /api/auth/logout | 로그아웃 |
| 거래처 | GET/POST /api/customers | 목록/생성 (ADMIN) |
| 품목 | GET/POST /api/items | 목록/생성 (ADMIN) |
| 플랜 | GET/POST /api/plans | 목록/생성 |
| 루트 | GET /api/routes/plan/{id} | 플랜별 루트 |
| 스탑 | GET /api/stops/route/{id} | 루트별 스탑 |
| 완료 | POST /api/completions/stop/{id} | 스탑 완료 (DRIVER) |
| 리포트 | GET /api/reports/monthly/pdf | 월말 PDF (ADMIN) |

## 보안

- 비밀번호: bcrypt 해시 (plain 저장 금지)
- 세션: DB `sessions` 테이블에 저장
- 쿠키: HttpOnly, Secure(옵션), SameSite=Lax
- Driver: 배정된 루트만 접근 가능 (서버에서 강제)

## 백업

```bash
# Linux/Mac
./scripts/backup.sh

# Windows
powershell -File scripts/backup.ps1
```

## 테스트

```bash
cd backend
export DATABASE_URL=postgresql://yummy:yummy_secret@localhost:5432/yummy
pytest tests/ -v
```

## 디렉터리 구조

```
yummy_server/
├── backend/
│   ├── app/
│   │   ├── api/         # 라우터
│   │   ├── core/        # auth, security
│   │   ├── models/      # SQLAlchemy 모델
│   │   ├── schemas/     # Pydantic
│   │   └── services/    # 리포트 등
│   ├── alembic/
│   └── tests/
├── frontend/static/     # 웹 정적 파일
├── scripts/             # 백업 등
└── docker-compose.yml
```
