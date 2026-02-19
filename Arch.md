# PairSpot — 情侶社交 App 架構規劃書

## 1. 產品概述

一款專為情侶設計的社交 App，以「一組帳號綁定兩人」為核心概念。MVP 階段聚焦於：註冊（雙 Email 驗證）、貼文（圖文）、個人檔案、帳號管理、內購付費。未來擴充私訊功能。

---

## 2. 系統架構總覽

```
┌──────────────┐     ┌──────────────┐
│  iOS App     │     │  Web SPA     │
│  (Swift)     │     │  (未來)       │
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                │  HTTPS / REST
                ▼
        ┌───────────────┐
        │  API Gateway  │  (Nginx / Traefik)
        │  Rate Limit   │
        │  SSL 終端      │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │  Python API   │  FastAPI (ASGI)
        │  Application  │  Gunicorn + Uvicorn workers
        └───┬───┬───┬───┘
            │   │   │
     ┌──────┘   │   └──────┐
     ▼          ▼          ▼
┌─────────┐ ┌───────┐ ┌──────────┐
│PostgreSQL│ │ Redis │ │ Object   │
│  (DB)   │ │(Cache)│ │ Storage  │
│         │ │       │ │ (S3相容) │
└─────────┘ └───────┘ └──────────┘
                         │
                    ┌────┘
                    ▼
              ┌──────────┐
              │   CDN    │
              │ (圖片分發)│
              └──────────┘
```

### 雲中立策略

| 元件 | 自建/容器化方案 | AWS 對應 | GCP 對應 |
|------|----------------|---------|---------|
| API Server | Docker + K8s | ECS / EKS | Cloud Run / GKE |
| PostgreSQL | Docker PostgreSQL | RDS PostgreSQL | Cloud SQL |
| Redis | Docker Redis | ElastiCache | Memorystore |
| Object Storage | MinIO (開發) | S3 | Cloud Storage |
| CDN | — | CloudFront | Cloud CDN |
| Email 寄送 | SMTP relay | SES | 第三方 (見下方) |
| 排程任務 | Celery + Redis | — | — |

**核心原則：所有服務透過 Docker Compose (開發) 及 Kubernetes Helm Charts (生產) 部署，不直接依賴任何雲端 SDK。Storage 層透過 S3 相容 API 抽象（MinIO / AWS S3 / GCS 均支援 S3 protocol）。**

---

## 3. 技術選型

### 3.1 後端：Python + FastAPI

| 選擇 | 理由 |
|------|------|
| **FastAPI** | 高效能 ASGI 框架、自動生成 OpenAPI docs（App & Web 共用）、原生 async 支援 |
| **SQLAlchemy 2.0** | ORM，支援 async，不綁定特定 DB |
| **Alembic** | DB Migration 管理 |
| **Pydantic v2** | Request/Response 驗證，與 FastAPI 深度整合 |
| **Celery + Redis** | 非同步任務（寄信、圖片處理、推播） |
| **Pillow / sharp** | 圖片壓縮、縮圖生成 |

### 3.2 前端：Swift (iOS)

| 選擇 | 理由 |
|------|------|
| **SwiftUI** | Apple 主推的 UI 框架，適合新專案 |
| **Swift Concurrency (async/await)** | 網路層使用 structured concurrency |
| **URLSession** | 原生網路請求，不需額外 dependency |
| **Kingfisher** | 圖片載入與快取 |
| **StoreKit 2** | In-App Purchase 處理 |
| **KeychainAccess** | Token 安全儲存 |

### 3.3 資料庫：PostgreSQL

**版本建議：PostgreSQL 16+**

選用理由：JSONB 彈性欄位、Full-text search（未來搜尋貼文）、Row Level Security（資料隔離）、成熟的 extension 生態系。

### 3.4 Email 寄送服務評估

針對社交類 App 的雙信箱驗證信需求，以下比較主流方案：

| 服務 | 免費額度 | 優勢 | 劣勢 | 雲中立 | 建議 |
|------|---------|------|------|--------|------|
| **Resend** | 3,000 封/月 | 開發體驗極佳、API 簡潔、支援 React Email 模板 | 較新的服務 | ✅ | ⭐ **MVP 首選** |
| **SendGrid (Twilio)** | 100 封/天 | 市佔高、功能完整、模板編輯器 | 免費額度低、設定複雜 | ✅ | 備選 |
| **Mailgun** | 100 封/天 (試用) | 高到達率、webhooks 完善 | 免費期短 | ✅ | 備選 |
| **Amazon SES** | $0.10/1000 封 | 極低成本 | 綁 AWS、初始需申請產線存取 | ❌ | 不建議 |
| **Postmark** | 100 封/月 | 到達率業界最高、專注交易信 | 免費額度極低 | ✅ | 量大後考慮 |

**建議：MVP 階段使用 Resend**
- 2,000 用戶 × 2 封驗證信 = 4,000 封（註冊期），之後每月通知信量預估 < 3,000 封
- Python SDK 安裝：`pip install resend`
- 純 API 呼叫，不綁定雲端，切換成本極低
- 支援自訂網域發信、到達率追蹤

**Email 服務抽象層設計：**
```python
# app/services/email/base.py
from abc import ABC, abstractmethod

class EmailProvider(ABC):
    @abstractmethod
    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        pass

# app/services/email/resend_provider.py
class ResendProvider(EmailProvider):
    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        # Resend API 實作
        ...

# 未來可輕鬆替換為 SendGridProvider, SESProvider 等
```

---

## 4. 資料庫設計 (PostgreSQL)

### 4.1 ER Diagram

```
┌─────────────────┐       ┌─────────────────────┐
│    couples      │       │      users           │
├─────────────────┤       ├─────────────────────┤
│ id (PK, UUID)   │◄──┐   │ id (PK, UUID)        │
│ anniversary_date │   │   │ couple_id (FK)       │
│ couple_name     │   └───│ email                │
│ avatar_url      │       │ password_hash        │
│ status          │       │ display_name         │
│ created_at      │       │ email_verified       │
│ deleted_at      │       │ role (partner_a/b)   │
└─────────────────┘       │ created_at           │
        │                 └──────────┬──────────┘
        │                            │
        ▼                            │
┌─────────────────────┐              │
│      posts          │              │
├─────────────────────┤              │
│ id (PK, UUID)       │              │
│ couple_id (FK)      │──────────────┘ (author_id FK → users)
│ author_id (FK)      │
│ content (TEXT)      │
│ visibility          │
│ is_promoted         │
│ promoted_until      │
│ like_count          │
│ created_at          │
│ updated_at          │
│ deleted_at          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   post_images       │
├─────────────────────┤
│ id (PK, UUID)       │
│ post_id (FK)        │
│ image_url           │
│ thumbnail_url       │
│ sort_order          │
│ width, height       │
│ created_at          │
└─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│      likes          │     │   coin_transactions  │
├─────────────────────┤     ├─────────────────────┤
│ id (PK, UUID)       │     │ id (PK, UUID)        │
│ post_id (FK)        │     │ user_id (FK)         │
│ user_id (FK)        │     │ type (purchase/spend) │
│ created_at          │     │ amount               │
│                     │     │ balance_after        │
│ UNIQUE(post_id,     │     │ apple_txn_id         │
│        user_id)     │     │ reference_id         │
└─────────────────────┘     │ created_at           │
                            └─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│  user_wallets       │     │   reports            │
├─────────────────────┤     ├─────────────────────┤
│ user_id (PK, FK)    │     │ id (PK, UUID)        │
│ balance (INT)       │     │ reporter_id (FK)     │
│ updated_at          │     │ post_id (FK)         │
└─────────────────────┘     │ reason               │
                            │ status               │
                            │ created_at           │
                            └─────────────────────┘
```

### 4.2 關鍵設計決策

**Couple 為核心實體**：一個 `couple` 下掛兩個 `user`，貼文屬於 couple 但記錄 author。這樣 couple profile 頁可以同時顯示兩人的共同貼文。

**Soft Delete**：`deleted_at` 欄位實現軟刪除，滿足 iOS App Review 的帳號注銷要求（Apple 要求 30 天內可恢復）。

**錢包與交易分離**：`user_wallets` 存餘額快照、`coin_transactions` 為不可變的交易紀錄（audit trail），確保點數一致性。

**促進曝光**：`is_promoted` + `promoted_until` 搭配 Feed 排序演算法加權。

### 4.3 索引規劃

```sql
-- 貼文 Feed 查詢（依時間 + 推廣排序）
CREATE INDEX idx_posts_feed ON posts (created_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_posts_promoted ON posts (promoted_until DESC)
    WHERE is_promoted = true AND deleted_at IS NULL;

-- 情侶貼文查詢
CREATE INDEX idx_posts_couple ON posts (couple_id, created_at DESC)
    WHERE deleted_at IS NULL;

-- 使用者查詢
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_couple ON users (couple_id);

-- 點讚查詢
CREATE INDEX idx_likes_post ON likes (post_id);
```

---

## 5. API 設計

### 5.1 API 規範

- RESTful API，JSON 格式
- 版本化路由：`/api/v1/...`
- JWT 認證（Access Token 15min + Refresh Token 30 days）
- OpenAPI 3.0 自動文件（FastAPI 內建）
- 統一錯誤格式

### 5.2 核心 Endpoints

```
Auth & Registration
───────────────────
POST   /api/v1/auth/register/initiate     # 建立 couple，發送兩封驗證信
POST   /api/v1/auth/register/verify       # 驗證 email token
POST   /api/v1/auth/register/complete     # 兩人都驗證後，設定密碼完成註冊
POST   /api/v1/auth/login                 # 登入（任一人）
POST   /api/v1/auth/token/refresh         # 刷新 Token
POST   /api/v1/auth/password/reset        # 忘記密碼

Couple Profile
───────────────────
GET    /api/v1/couples/{id}               # 取得情侶檔案
PATCH  /api/v1/couples/{id}               # 更新檔案（名稱、交往日期）
PUT    /api/v1/couples/{id}/avatar        # 上傳情侶頭貼（multipart）

Posts
───────────────────
GET    /api/v1/posts                      # Feed（分頁，promoted 優先）
POST   /api/v1/posts                      # 建立貼文（multipart: 圖片+文字）
GET    /api/v1/posts/{id}                 # 單篇貼文
PATCH  /api/v1/posts/{id}                 # 編輯貼文（僅 author）
DELETE /api/v1/posts/{id}                 # 刪除貼文（soft delete）
POST   /api/v1/posts/{id}/like            # 按讚
DELETE /api/v1/posts/{id}/like            # 取消讚
POST   /api/v1/posts/{id}/report          # 檢舉

Wallet & IAP
───────────────────
GET    /api/v1/wallet                     # 查詢餘額
POST   /api/v1/wallet/verify-receipt      # Apple IAP 收據驗證
POST   /api/v1/posts/{id}/promote         # 花費點數推廣貼文

Account
───────────────────
GET    /api/v1/account                    # 帳號資訊
PATCH  /api/v1/account                    # 更新個人資料
DELETE /api/v1/account                    # 帳號注銷（soft delete）
POST   /api/v1/account/restore            # 30天內恢復帳號

(預留) Messaging
───────────────────
# WebSocket /api/v1/ws/chat              # 未來私訊
# GET    /api/v1/conversations            # 未來對話列表
```

### 5.3 註冊流程

```
Partner A 發起 ──▶ POST /register/initiate
                    │  body: { email_a, email_b, couple_name, anniversary }
                    │
                    ▼
              建立 couple (status: pending)
              建立 user_a (unverified), user_b (unverified)
              發送驗證信 → email_a ✉️
              發送驗證信 → email_b ✉️
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               │
Partner A 點擊   Partner B 點擊      │
驗證連結          驗證連結            │  (兩人各自驗證)
POST /verify     POST /verify       │
    │               │               │
    ▼               ▼               │
user_a.verified  user_b.verified    │
= true           = true            │
    │               │               │
    └───────┬───────┘               │
            ▼                       │
    兩人都驗證完成？ ──── No ────────┘
            │ Yes
            ▼
    POST /register/complete
    { passwords for both users }
    couple.status = active ✅
```

---

## 6. 圖片處理架構

```
iOS App
  │  選圖 + 壓縮 (client-side, max 2MB)
  │
  ▼
POST /api/v1/posts (multipart/form-data)
  │
  ▼
FastAPI ──▶ 儲存原圖至 Object Storage (S3 相容)
       ──▶ 發送 Celery Task
                │
                ▼
         Celery Worker
         ├── 生成縮圖 (300x300)
         ├── 生成中圖 (800px wide)
         ├── Strip EXIF metadata
         └── 上傳至 Object Storage
                │
                ▼
         CDN 分發 (Cache-Control: 1 year)
```

**儲存路徑規範：**
```
/couples/{couple_id}/posts/{post_id}/original_{uuid}.jpg
/couples/{couple_id}/posts/{post_id}/medium_{uuid}.jpg
/couples/{couple_id}/posts/{post_id}/thumb_{uuid}.jpg
/couples/{couple_id}/avatar/original_{uuid}.jpg
/couples/{couple_id}/avatar/thumb_{uuid}.jpg
```

---

## 7. In-App Purchase (StoreKit 2)

### 7.1 流程

```
iOS App                          Backend
  │                                │
  │ 1. 顯示點數方案                  │
  │    (50點/$0.99, 150點/$2.99)    │
  │                                │
  │ 2. User 購買 (StoreKit 2)      │
  │    Apple 回傳 Transaction       │
  │                                │
  │ 3. POST /wallet/verify-receipt │
  │    { signedTransaction }  ────▶│
  │                                │ 4. 驗證 Apple JWS
  │                                │    (App Store Server API)
  │                                │ 5. 寫入 coin_transactions
  │                                │    更新 user_wallets.balance
  │◀──── { balance: 150 } ────────│
  │                                │
  │ 6. POST /posts/{id}/promote    │
  │    { coins: 30, days: 3 } ───▶│
  │                                │ 7. 扣款 + 設定 promoted_until
  │◀──── { success, balance: 120 }│
```

### 7.2 Apple 審核注意事項

- 所有虛擬貨幣 **必須** 透過 IAP，不可使用第三方支付
- App 內必須明確顯示「促進曝光」的效果說明
- 帳號注銷功能必須存在且容易找到（Settings 內 1-2 步到達）
- 注銷後必須停止資料收集，30 天後可永久刪除
- 必須提供隱私權政策與使用條款連結

---

## 8. 安全性設計

### 8.1 認證與授權

```
JWT Token 策略
├── Access Token:  15 分鐘過期、RS256 簽章
├── Refresh Token: 30 天過期、儲存於 DB（可撤銷）
└── Token 包含:    user_id, couple_id, role

權限規則
├── 貼文 CRUD:   僅 couple 成員（author 可編輯/刪除）
├── 檔案更新:    couple 任一成員
├── 帳號注銷:    僅本人（另一半的帳號不受影響，couple 降級為 single）
└── 錢包:       僅本人
```

### 8.2 資料保護

- 密碼：bcrypt (cost factor 12)
- API 傳輸：TLS 1.3
- 圖片：上傳時 strip EXIF（含 GPS 資訊）
- 敏感欄位：email 加密儲存 (AES-256)，搜尋用 hash index
- Rate Limiting：註冊 5 次/小時/IP、登入 10 次/分鐘/IP

---

## 9. 專案結構

### 9.1 後端

```
backend/
├── docker-compose.yml          # 本地開發環境
├── Dockerfile
├── pyproject.toml              # 使用 Poetry 或 uv 管理依賴
├── alembic/                    # DB migrations
│   └── versions/
├── app/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (pydantic-settings)
│   ├── dependencies.py         # DI (DB session, current_user)
│   ├── models/                 # SQLAlchemy models
│   │   ├── couple.py
│   │   ├── user.py
│   │   ├── post.py
│   │   └── wallet.py
│   ├── schemas/                # Pydantic request/response
│   │   ├── auth.py
│   │   ├── post.py
│   │   └── wallet.py
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── couples.py
│   │       ├── posts.py
│   │       ├── wallet.py
│   │       └── account.py
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── post_service.py
│   │   ├── image_service.py
│   │   ├── iap_service.py
│   │   └── email/
│   │       ├── base.py
│   │       └── resend_provider.py
│   ├── tasks/                  # Celery tasks
│   │   ├── image_tasks.py
│   │   └── email_tasks.py
│   ├── core/
│   │   ├── security.py         # JWT, hashing
│   │   ├── storage.py          # S3 相容 storage client
│   │   └── exceptions.py
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       └── test_posts.py
├── scripts/
│   └── seed.py                 # 測試資料
└── k8s/                        # Kubernetes manifests
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml
```

### 9.2 iOS App

```
CoupleSpace/
├── CoupleSpace.xcodeproj
├── CoupleSpace/
│   ├── App/
│   │   ├── CoupleSpaceApp.swift
│   │   └── AppDelegate.swift
│   ├── Core/
│   │   ├── Network/
│   │   │   ├── APIClient.swift         # URLSession wrapper
│   │   │   ├── AuthInterceptor.swift   # Token refresh
│   │   │   ├── Endpoints.swift
│   │   │   └── APIError.swift
│   │   ├── Storage/
│   │   │   ├── KeychainManager.swift
│   │   │   └── UserDefaults+Ext.swift
│   │   └── Models/
│   │       ├── Couple.swift
│   │       ├── Post.swift
│   │       └── User.swift
│   ├── Features/
│   │   ├── Auth/
│   │   │   ├── Views/
│   │   │   │   ├── RegisterView.swift
│   │   │   │   ├── VerificationView.swift
│   │   │   │   └── LoginView.swift
│   │   │   └── ViewModels/
│   │   │       └── AuthViewModel.swift
│   │   ├── Feed/
│   │   │   ├── Views/
│   │   │   │   ├── FeedView.swift
│   │   │   │   └── PostCardView.swift
│   │   │   └── ViewModels/
│   │   │       └── FeedViewModel.swift
│   │   ├── Profile/
│   │   │   ├── Views/
│   │   │   │   ├── ProfileView.swift
│   │   │   │   └── EditProfileView.swift
│   │   │   └── ViewModels/
│   │   │       └── ProfileViewModel.swift
│   │   ├── CreatePost/
│   │   │   ├── Views/
│   │   │   │   └── CreatePostView.swift
│   │   │   └── ViewModels/
│   │   │       └── CreatePostViewModel.swift
│   │   ├── Store/
│   │   │   ├── Views/
│   │   │   │   └── StoreView.swift
│   │   │   └── StoreManager.swift      # StoreKit 2
│   │   └── Settings/
│   │       ├── Views/
│   │       │   ├── SettingsView.swift
│   │       │   └── DeleteAccountView.swift
│   │       └── ViewModels/
│   │           └── SettingsViewModel.swift
│   ├── Shared/
│   │   ├── Components/
│   │   │   ├── CoupleAvatarView.swift
│   │   │   ├── DaysTogetherBadge.swift
│   │   │   └── ImagePicker.swift
│   │   └── Extensions/
│   │       ├── Date+Ext.swift
│   │       └── View+Ext.swift
│   └── Resources/
│       └── Assets.xcassets
└── CoupleSpaceTests/
```

---

## 10. 2,000 人規模基礎設施評估

### 10.1 流量預估

| 指標 | 數值 | 備註 |
|------|------|------|
| 註冊用戶 | 2,000 人 (1,000 對情侶) | |
| DAU | ~600 人 (30%) | 社交 App 平均 |
| 每日貼文 | ~100 篇 | |
| 每日 API 請求 | ~30,000 | 含瀏覽、按讚等 |
| 每日圖片上傳 | ~200 張 | 平均每篇 2 張 |
| Storage 月成長 | ~2 GB | 含縮圖 |
| 高峰 QPS | ~10 | |

### 10.2 推薦部署方案

**MVP 階段（省成本）：單機部署即可**

```
1 台 VPS (4 vCPU, 8GB RAM)
├── Docker Compose
│   ├── Nginx         (reverse proxy)
│   ├── FastAPI × 2   (Gunicorn workers)
│   ├── Celery × 1    (worker)
│   ├── PostgreSQL     (with daily pg_dump backup)
│   ├── Redis          (cache + Celery broker)
│   └── MinIO          (S3 相容，開發/小規模用)
│
└── 預估月費：$20-40 (DigitalOcean / Vultr / Linode)
```

**成長階段（5,000+ 用戶）切換至：**

```
Container Orchestration (K8s / ECS / Cloud Run)
├── API: 2-4 replicas (auto-scaling)
├── Celery: 1-2 workers
├── PostgreSQL: Managed service (RDS / Cloud SQL)
├── Redis: Managed service
├── Object Storage: S3 / GCS (取代 MinIO)
└── CDN: CloudFront / Cloud CDN
```

### 10.3 成本估算 (MVP)

| 項目 | 月費 (USD) |
|------|-----------|
| VPS (4C/8G) | $24 |
| Domain + SSL (Let's Encrypt) | $1 |
| Resend (Email) | $0 (免費額度) |
| Apple Developer Program | $8.25 (年費 $99) |
| Object Storage (初期 MinIO) | $0 (同機) |
| **Total** | **~$33/月** |

---

## 11. 未來擴充規劃

### 11.1 私訊功能（Phase 2）

```
技術選型：
├── WebSocket (FastAPI WebSocket support)
├── Message Queue: Redis Pub/Sub → 未來可遷移至 NATS
├── 訊息儲存: PostgreSQL (messages table)
└── 離線推播: APNs (Apple Push Notification service)

DB 擴充：
├── conversations (id, couple_a_id, couple_b_id, ...)
├── messages (id, conversation_id, sender_id, content, ...)
└── read_receipts (message_id, user_id, read_at)
```

### 11.2 其他可能擴充

- 限時動態 (Stories)：需排程刪除 task
- 紀念日提醒：Push notification + 日曆整合
- 情侶間私密相簿：加密 storage bucket
- Android 版：共用同一套 API
- Web 版：React / Next.js，共用同一套 API

---

## 12. 開發里程碑建議

| 階段 | 週期 | 內容 |
|------|------|------|
| **Phase 0** | Week 1-2 | 環境建置、Docker Compose、DB schema、CI/CD pipeline |
| **Phase 1** | Week 3-5 | 註冊/登入流程（含 email 驗證）、JWT 認證 |
| **Phase 2** | Week 6-8 | 貼文 CRUD、圖片上傳/處理、Feed API |
| **Phase 3** | Week 9-10 | 情侶檔案、頭貼上傳、在一起天數 |
| **Phase 4** | Week 11-12 | IAP 整合、點數系統、推廣貼文 |
| **Phase 5** | Week 13-14 | 帳號注銷、iOS App Review 合規檢查 |
| **Phase 6** | Week 15-16 | 測試、效能調優、App Store 送審 |

---

## 13. 決策待確認項目

1. **Feed 演算法**：純時間排序 vs 加入互動權重？MVP 建議先用時間排序 + promoted 置頂
2. **情侶解綁**：分手後帳號如何處理？建議各自保留帳號但 couple 凍結
3. **多對情侶互動**：Feed 是否只看自己的貼文？還是也能看到其他情侶？（若為後者，需要 follow 機制）
4. **內容審核**：是否需要 AI 或人工審核貼文？Apple 可能會要求檢舉機制
5. **Push Notification**：MVP 是否需要？建議至少做「另一半發文通知」