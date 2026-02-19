# PairSpot Backend

情侶社交 App 後端 API 服務

## 技術架構

- **框架**: FastAPI + SQLAlchemy 2.0 (async)
- **資料庫**: PostgreSQL 16
- **快取**: Redis
- **任務佇列**: Celery
- **物件儲存**: S3 相容 (MinIO/AWS S3/GCS)
- **Email**: Resend

## 本地開發

### 前置需求

- Python 3.9+
- Docker & Docker Compose

### 首次設定

```bash
cd backend

# 1. 複製環境變數範本
cp .env.example .env

# 2. 啟動基礎服務 (PostgreSQL, Redis, MinIO)
docker compose up -d

# 3. 等待服務啟動 (約 5-10 秒)
docker compose ps  # 確認所有服務為 running 狀態

# 4. 安裝 Python 依賴
python3 -m pip install -e ".[dev]"

# 5. 執行資料庫遷移
alembic upgrade head

# 6. 啟動 API 服務
uvicorn app.main:app --reload
```

### 日常開發

```bash
# 啟動服務
docker compose up -d
uvicorn app.main:app --reload

# 停止服務
docker compose down

# 查看服務狀態
docker compose ps

# 查看 logs
docker compose logs -f api
docker compose logs -f db
```

### 資料庫操作

```bash
# 執行遷移
alembic upgrade head

# 建立新的遷移檔 (自動偵測 model 變更)
alembic revision --autogenerate -m "Add new table"

# 回滾一個版本
alembic downgrade -1

# 查看遷移歷史
alembic history

# 重置資料庫 (⚠️ 會清除所有資料)
docker compose exec db psql -U pairspot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head

# 填入測試資料
python scripts/seed.py
```

### 執行測試

```bash
# 執行所有測試
pytest -v

# 執行特定測試檔
pytest app/tests/test_auth.py -v

# 顯示覆蓋率報告
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### 程式碼品質

```bash
# Lint 檢查
ruff check app/

# 自動修復
ruff check app/ --fix

# 格式化
ruff format app/

# Type 檢查
mypy app/
```

## API 文件

啟動服務後訪問:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## 服務端口

| 服務 | 端口 | 說明 |
|------|------|------|
| API | 8000 | FastAPI 應用 |
| PostgreSQL | 5432 | 資料庫 |
| Redis | 6379 | 快取 / Celery Broker |
| MinIO API | 9000 | S3 相容物件儲存 |
| MinIO Console | 9001 | MinIO 管理介面 |

## 專案結構

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # 核心模組 (DB, security, storage)
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── tasks/           # Celery tasks
│   └── tests/           # 測試
├── alembic/             # 資料庫遷移
│   └── versions/        # 遷移檔案
├── scripts/             # 工具腳本
├── k8s/                 # Kubernetes 部署配置
├── docker-compose.yml   # 本地開發環境
├── Dockerfile           # 容器映像檔
└── pyproject.toml       # 專案設定與依賴
```

## 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql+asyncpg://pairspot:pairspot@localhost:5432/pairspot` |
| `REDIS_URL` | Redis 連線字串 | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT 簽章密鑰 | (必填) |
| `S3_ENDPOINT_URL` | S3 端點 | `http://localhost:9000` |
| `S3_ACCESS_KEY` | S3 存取金鑰 | `minioadmin` |
| `S3_SECRET_KEY` | S3 私密金鑰 | `minioadmin` |
| `RESEND_API_KEY` | Resend Email API Key | (選填) |

## 疑難排解

### 資料庫連線失敗

```bash
# 確認 PostgreSQL 容器正在運行
docker compose ps

# 重啟資料庫
docker compose restart db

# 查看資料庫 logs
docker compose logs db
```

### 遷移衝突 (type already exists)

```bash
# 重置資料庫 schema
docker compose exec db psql -U pairspot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
```

### 端口被佔用

```bash
# 找出佔用端口的程序
lsof -i :8000

# 終止程序
kill -9 <PID>
```

### Python 版本問題

確保使用正確的 Python 版本：

```bash
# 檢查版本
python --version

# 使用指定版本的 pip
python -m pip install -e ".[dev]"
```
