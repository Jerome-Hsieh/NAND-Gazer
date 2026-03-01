# Price Tracker - 電商商品價格追蹤系統

以 Airflow 為核心的電商商品價格追蹤系統，爬取 PChome 24h 的商品價格，存入 PostgreSQL，透過 FastAPI 提供 REST API，並用 React 前端呈現價格趨勢圖表。

## 目錄

- [系統架構](#系統架構)
- [技術棧](#技術棧)
- [專案目錄結構](#專案目錄結構)
- [資料庫設計](#資料庫設計)
- [方法一：本地開發環境](#方法一本地開發環境devcontainer--debian)
- [方法二：Docker Compose 部署](#方法二docker-compose-部署)
- [API 端點說明](#api-端點說明)
- [Airflow DAG 說明](#airflow-dag-說明)
- [E2E 測試](#e2e-測試)
- [管理追蹤的關鍵字](#管理追蹤的關鍵字)
- [常見問題排除](#常見問題排除)

## 系統架構

### 整體流程圖

```mermaid
flowchart TB
    subgraph External["外部資料來源"]
        PChome["🛒 PChome 24h<br/>Search API v4.3"]
    end

    subgraph Airflow["⏰ Apache Airflow 3.0 (排程引擎)"]
        Scheduler["Scheduler<br/>排程器"]
        DAG1["pchome_price_scraper<br/>每 6 小時"]
        DAG2["price_data_cleanup<br/>每日 02:00"]
        Scheduler --> DAG1
        Scheduler --> DAG2
    end

    subgraph Backend["🖥️ FastAPI 後端 (port 8000)"]
        API["REST API<br/>/api/v1/*"]
        Cache["Redis 快取<br/>pricetracker:*"]
        API <-->|"查詢/失效"| Cache
    end

    subgraph Frontend["🌐 React 前端"]
        Nginx["Nginx (Docker, port 80)<br/>或 Vite Dev Server (port 5173)"]
        SPA["React SPA<br/>Dashboard / Search / Detail"]
        Nginx --> SPA
    end

    subgraph Storage["💾 資料儲存"]
        PG[("PostgreSQL<br/>products, price_history,<br/>tracked_keywords, scrape_jobs")]
        MV["mv_latest_prices<br/>Materialized View"]
        Redis[("Redis 7<br/>快取層")]
        PG --- MV
    end

    User(("👤 使用者"))

    %% Data flow
    DAG1 -->|"HTTP 爬取"| PChome
    PChome -->|"商品 + 價格 JSON"| DAG1
    DAG1 -->|"UPSERT 商品<br/>INSERT 價格"| PG
    DAG1 -->|"REFRESH MV"| MV
    DAG1 -->|"清除快取"| Redis
    DAG2 -->|"刪除 90 天舊資料<br/>VACUUM ANALYZE"| PG

    API -->|"async 查詢"| PG
    Cache -.->|"讀寫"| Redis

    SPA -->|"fetch /api/v1/*"| Nginx
    Nginx -->|"反向代理"| API

    User -->|"瀏覽"| Nginx
```

### 資料流程

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant D as Scraper DAG
    participant P as PChome API
    participant DB as PostgreSQL
    participant R as Redis
    participant A as FastAPI
    participant F as Frontend
    participant U as 使用者

    Note over S,D: 每 6 小時自動觸發（或手動觸發）

    S->>D: 觸發 pchome_price_scraper
    D->>DB: 讀取 tracked_keywords
    DB-->>D: [DDR5 記憶體, DDR4 記憶體, ...]

    loop 每個關鍵字
        D->>P: GET /ecapi/ecshop/search/v4.3/[keyword]
        P-->>D: 商品列表 JSON
        D->>DB: UPSERT products + INSERT price_history
        D->>DB: INSERT scrape_jobs (status=success)
    end

    D->>DB: REFRESH MATERIALIZED VIEW mv_latest_prices
    D->>R: DEL pricetracker:*

    Note over U,F: 使用者瀏覽網頁

    U->>F: 開啟 http://localhost
    F->>A: GET /api/v1/stats
    A->>R: 查詢快取
    alt 快取命中
        R-->>A: cached JSON
    else 快取未命中
        A->>DB: SELECT count(*), ...
        DB-->>A: 統計數據
        A->>R: 寫入快取
    end
    A-->>F: {total_products, active_keywords, ...}
    F-->>U: 顯示 Dashboard 統計卡片 + 商品列表
```

### Docker Compose 服務關係

```mermaid
flowchart LR
    subgraph docker["Docker Compose"]
        PG[("postgres<br/>:5432")]
        RD[("redis<br/>:6379")]

        AI["airflow-init"] -->|db migrate| PG
        AS["airflow-api-server<br/>:8081"] -->|depends| AI
        ASC["airflow-scheduler"] -->|depends| AS
        ADP["airflow-dag-processor"] -->|depends| AS

        ASC -->|讀寫| PG
        ASC -->|讀寫| RD
        AS -->|讀寫| PG

        API["api (FastAPI)<br/>:8000"]
        API -->|asyncpg| PG
        API -->|cache| RD

        FE["frontend (Nginx)<br/>:80"]
        FE -->|"/api/* proxy"| API
    end

    User(("使用者")) -->|":80"| FE
    User -->|":8081"| AS
```

## 技術棧


| 層級       | 技術                 | 版本                           |
| -------- | ------------------ | ---------------------------- |
| 排程引擎     | Apache Airflow     | 3.0.1                        |
| 後端 API   | FastAPI + Uvicorn  | latest                       |
| 資料庫      | PostgreSQL         | 15 (本地) / 17-alpine (Docker) |
| 快取       | Redis              | 7                            |
| 前端       | React + TypeScript | 19.2 + 5.9                   |
| 建置工具     | Vite               | 7.3                          |
| CSS 框架   | TailwindCSS        | 4.2 (v4 架構)                  |
| 圖表       | Recharts           | 3.7                          |
| API 狀態管理 | TanStack Query     | 5.90                         |
| 路由       | React Router       | 7                            |
| 測試框架     | pytest + Playwright | pytest 8 + Playwright latest |


## 專案目錄結構

```
price-tracker/
├── .env                          # 環境變數（本地開發用）
├── .env.example                  # 環境變數範本
├── .gitignore
├── docker-compose.yml            # Docker 部署配置
├── README.md
│
├── postgres/
│   └── init/
│       ├── 00_create_airflow_db.sql  # 建立 Airflow DB
│       ├── 01_schema.sql             # 資料庫 schema（5 張表 + MV + 索引）
│       └── 02_seed_data.sql          # PChome 記憶體商品種子資料
│
├── airflow/
│   ├── Dockerfile                    # 基於 apache/airflow:3.0.1-python3.11
│   ├── requirements.txt              # 額外依賴（httpx, tenacity 等）
│   ├── dags/
│   │   ├── pchome_scraper_dag.py # 每 6 小時爬取 PChome 價格
│   │   └── price_cleanup_dag.py  # 每日 02:00 清理舊資料
│   └── include/
│       └── scraper/
│           └── pchome/
│               ├── client.py     # HTTP client（httpx 同步 + retry）
│               ├── parser.py     # 解析 PChome v4.3 Search API
│               └── models.py     # PChomeProduct dataclass
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                   # FastAPI 應用入口
│   ├── config.py                 # pydantic-settings 設定
│   ├── db/
│   │   ├── database.py           # SQLAlchemy async engine
│   │   └── crud.py               # 資料庫查詢函式
│   ├── models/
│   │   └── schemas.py            # Pydantic response models
│   ├── routers/
│   │   ├── products.py           # GET /products, GET /products/{id}
│   │   ├── prices.py             # GET /products/{id}/prices
│   │   └── stats.py              # GET /stats
│   └── cache/
│       └── redis_client.py       # Redis 快取工具
│
├── tests/
│   ├── conftest.py               # Root fixtures（httpx, psycopg2, redis）
│   ├── pytest.ini                # pytest 設定
│   ├── requirements-test.txt     # 測試依賴
│   ├── e2e/
│   │   ├── test_00_infrastructure.py  # 服務連通性（5 tests）
│   │   ├── test_01_database.py        # Schema/seed/indexes（7 tests）
│   │   ├── test_02_api.py             # API 端點（12 tests）
│   │   ├── test_03_airflow_dags.py    # DAG 觸發+執行（11 tests）
│   │   ├── test_04_frontend.py        # Playwright 瀏覽器（17 tests）
│   │   └── test_05_full_pipeline.py   # 完整 pipeline（1 test）
│   └── utils/
│       ├── airflow_client.py     # Airflow REST API v2 helper
│       └── wait_helpers.py       # Polling 工具
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf                # 生產環境 Nginx 反向代理
    ├── package.json
    ├── vite.config.ts            # Vite 7 + TailwindCSS v4 plugin
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx               # React Router + TanStack Query Provider
        ├── types/index.ts        # TypeScript 型別定義
        ├── services/api.ts       # API 呼叫函式（使用相對路徑 /api/v1）
        ├── hooks/useProducts.ts  # TanStack Query hooks
        ├── components/
        │   ├── Layout/Header.tsx # 頂部導航列
        │   ├── ProductCard.tsx   # 商品卡片元件
        │   ├── PriceChart.tsx    # Recharts 價格折線圖
        │   └── StatsCard.tsx     # 統計數字卡片
        └── pages/
            ├── HomePage.tsx      # 儀表板首頁
            ├── SearchPage.tsx    # 商品搜尋頁（分頁）
            └── ProductDetailPage.tsx # 商品詳情 + 價格歷史圖表
```

## 資料庫設計

### 資料表


| 資料表                | 說明                                                           |
| ------------------ | ------------------------------------------------------------ |
| `shops`            | 賣家資訊 (platform, shop_id, name)                               |
| `products`         | 商品基本資訊 (item_id, name, url, category, brand)                 |
| `price_history`    | 價格時序資料 (price, original_price, discount_percent, scraped_at) |
| `tracked_keywords` | 追蹤的搜尋關鍵字，DAG 據此決定爬取哪些關鍵字                                     |
| `scrape_jobs`      | 爬取任務紀錄，用於監控爬蟲執行狀態                                            |


### 效能優化

- **Materialized View** `mv_latest_prices`：每個商品的最新價格快照，每次爬取後自動 refresh
- **複合索引** `(product_id, scraped_at DESC)` on `price_history`：加速價格歷史查詢
- **部分索引** `is_active = TRUE` on `products`：只索引活躍商品

### ER 關聯

```
shops (1) ──< products (1) ──< price_history (多)
tracked_keywords ──> [DAG 讀取] ──> scrape_jobs
```

---

## 方法一：本地開發環境（Devcontainer / Debian）

適用於在 Docker devcontainer 或任何 Debian/Ubuntu 系統中直接執行。

### 1. 安裝系統依賴

```bash
# 安裝 Python 3、PostgreSQL 15、Redis
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-client redis-server libpq-dev build-essential curl
```

### 2. 啟動基礎服務

```bash
# 啟動 PostgreSQL
sudo pg_ctlcluster 15 main start

# 啟動 Redis
sudo redis-server --daemonize yes
```

### 3. 設定 PostgreSQL 認證

有兩種方式可以解決 asyncpg 連線認證問題：

**方式 A：設定使用者密碼（建議）**

```bash
sudo -u postgres psql -c "ALTER USER $(whoami) WITH PASSWORD '$(whoami)';"
```

然後在 `.env` 中使用帶密碼的連線字串：

```
DATABASE_URL=postgresql+asyncpg://node:node@localhost:5432/pricetracker
```

**方式 B：改為 trust 模式**

```bash
sudo sed -i 's/peer$/trust/' /etc/postgresql/15/main/pg_hba.conf
sudo sed -i 's/scram-sha-256$/trust/' /etc/postgresql/15/main/pg_hba.conf
sudo pg_ctlcluster 15 main restart
```

> **注意**：asyncpg（API 使用的 async PostgreSQL driver）透過 TCP 連線，需要密碼認證或 trust 模式。`psql` 使用 Unix socket 的 peer 認證，所以可能 `psql` 能連但 API 連不上。

### 4. 建立資料庫與使用者

```bash
sudo -u postgres createuser -s $(whoami)
sudo -u postgres createdb pricetracker
sudo -u postgres createdb airflow
```

### 5. 執行資料庫 Schema 與種子資料

```bash
psql -d pricetracker -f postgres/init/01_schema.sql
psql -d pricetracker -f postgres/init/02_seed_data.sql
```

驗證：

```bash
psql -d pricetracker -c "\dt"
# 應看到 5 張表：shops, products, price_history, tracked_keywords, scrape_jobs

psql -d pricetracker -c "SELECT * FROM tracked_keywords;"
# 應看到 2 筆預設關鍵字：DDR5 記憶體, DDR4 記憶體

psql -d pricetracker -c "SELECT count(*) FROM products;"
# 種子資料應有 10 筆 PChome 記憶體商品
```

### 6. 建立 Python 虛擬環境並安裝依賴

使用 **uv**（建議）：

```bash
pip install --break-system-packages uv
export PATH="$HOME/.local/bin:$PATH"

cd /workspace/price-tracker
uv venv .venv
source .venv/bin/activate

uv pip install "apache-airflow==3.0.1" \
    "fastapi[standard]" \
    "sqlalchemy[asyncio]" \
    asyncpg httpx redis psycopg2-binary pydantic-settings
```

或使用傳統 venv：

```bash
cd /workspace/price-tracker
python3 -m venv .venv
source .venv/bin/activate

pip install "apache-airflow==3.0.1" \
    "fastapi[standard]" \
    "sqlalchemy[asyncio]" \
    asyncpg httpx redis psycopg2-binary pydantic-settings
```

### 7. 啟動 FastAPI 後端

```bash
cd /workspace/price-tracker
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

驗證：

```bash
# 健康檢查
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}

# 儀表板統計
curl 'http://localhost:8000/api/v1/stats'

# 商品列表
curl 'http://localhost:8000/api/v1/products'

# Swagger 文件
# 瀏覽器開啟 http://localhost:8000/docs
```

> **zsh 使用者注意**：URL 中的 `?` 會被 zsh 當作 glob 字元，請用單引號包裹 URL，例如 `curl 'http://localhost:8000/api/v1/products?page_size=3'`。

### 8. 啟動 React 前端開發伺服器

```bash
cd /workspace/price-tracker/frontend
npm install
npm run dev
```

前端運行在 `http://localhost:5173`，已設定 Vite proxy 將 `/api` 請求轉發到後端 `localhost:8000`。

### 9. 初始化並啟動 Airflow

```bash
cd /workspace/price-tracker
source .venv/bin/activate

# 設定 Airflow 環境變數
export AIRFLOW_HOME=/workspace/price-tracker/airflow
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://$(whoami)@localhost:5432/airflow
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DAGS_FOLDER=/workspace/price-tracker/airflow/dags

# 爬蟲 DAG 需要的環境變數
export PRICETRACKER_DB_CONN=postgresql://$(whoami):$(whoami)@localhost:5432/pricetracker
export PRICETRACKER_REDIS_URL=redis://localhost:6379/0

# 初始化 Airflow 資料庫
airflow db migrate

# 建立管理員帳號（首次啟動時需要）
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# 啟動 Airflow（standalone 模式，包含 webserver + scheduler）
airflow standalone
```

Airflow Web UI：`http://localhost:8080`（帳號密碼：admin / admin，或查看 standalone 輸出的密碼）

### 10. 手動觸發爬蟲 DAG

在 Airflow Web UI 中：

1. 找到 `pchome_price_scraper` DAG
2. 點擊開關啟用 DAG（取消暫停）
3. 點擊 "Trigger DAG" 手動觸發
4. 等待 DAG 執行完畢（可在 Graph View 觀察進度）

或使用 CLI：

```bash
# 取消暫停
airflow dags unpause pchome_price_scraper

# 手動觸發
airflow dags trigger pchome_price_scraper

# 查看最近的 DAG 執行結果
airflow dags list-runs -d pchome_price_scraper
```

### 11. 驗證完整流程

```bash
# 確認資料庫有資料
psql -d pricetracker -c "SELECT count(*) FROM products;"
psql -d pricetracker -c "SELECT count(*) FROM price_history;"
psql -d pricetracker -c "SELECT name, price, scraped_at FROM mv_latest_prices LIMIT 5;"

# 確認 API 回傳資料
curl 'http://localhost:8000/api/v1/products' | python3 -m json.tool
curl 'http://localhost:8000/api/v1/stats' | python3 -m json.tool

# 確認 Redis 快取
redis-cli keys "pricetracker:*"

# 瀏覽器開啟前端
# http://localhost:5173 → 應顯示儀表板與商品卡片
```

---

## 方法二：Docker Compose 部署

適用於有 Docker daemon 的環境（生產或測試伺服器）。

### 1. 準備環境變數

```bash
cd /workspace/price-tracker
cp .env.example .env
# 編輯 .env 中的變數（Docker 模式下主要由 docker-compose.yml 中的 environment 控制）
```

### 2. 啟動所有服務

```bash
docker compose up -d --build
```

> **首次啟動注意**：如果之前跑過舊版 compose，建議先清除舊資料再重建：
>
> ```bash
> docker compose down -v
> docker compose up -d --build
> ```
>
> `-v` 會刪除 PostgreSQL volume，確保 init scripts 重新執行。

此命令會啟動 8 個容器（含一次性 init）：


| 服務                      | 連接埠  | 說明                                           |
| ----------------------- | ---- | -------------------------------------------- |
| `postgres`              | 5432 | PostgreSQL 17，自動建立 `airflow` DB 與 app schema |
| `redis`                 | 6379 | Redis 7 快取                                   |
| `airflow-init`          | —    | 一次性：執行 `db migrate` + 建立 admin 帳號            |
| `airflow-api-server`    | 8081 | Airflow Web UI（免登入，已啟用 all_admins 模式）        |
| `airflow-dag-processor` | —    | Airflow DAG 解析器                              |
| `airflow-scheduler`     | —    | Airflow 排程器（無對外連接埠）                          |
| `api`                   | 8000 | FastAPI 後端                                   |
| `frontend`              | 80   | Nginx 提供前端靜態檔案 + 反向代理 `/api` → `api:8000`   |


> **請求流程**：瀏覽器 → `http://localhost` → Nginx（port 80）→ 靜態檔案（React SPA）或反向代理 `/api/*` → FastAPI（port 8000）。前端使用相對路徑 `/api/v1` 呼叫 API，由 Nginx 統一代理，無跨域問題。


### 3. 確認所有容器正常

```bash
docker compose ps
```

所有服務的 STATUS 應為 `Up`（`airflow-init` 為 `Exited (0)` 是正常的）。
如果有容器 `Restarting`，查看日誌排查：

```bash
docker compose logs api
docker compose logs airflow-api-server
```

### 4. 驗證服務

```bash
# 直接存取 API
curl http://localhost:8000/api/v1/health
# → {"status":"ok","version":"1.0.0"}

# 透過 Nginx 反向代理存取 API
curl http://localhost/api/v1/health
# → {"status":"ok","version":"1.0.0"}

# 開啟瀏覽器
# 前端：http://localhost
# Airflow：http://localhost:8081（免登入）
# API Swagger 文件：http://localhost:8000/docs
```

### 5. 首次啟動後觸發爬蟲

首次啟動後資料庫只有種子資料（schema + tracked_keywords），需要觸發 DAG 來爬取商品：

1. 開啟 Airflow Web UI：`http://localhost:8081`
2. 找到 `pchome_price_scraper` DAG，點擊開關啟用（取消暫停）
3. 點擊 "Trigger DAG" 手動觸發
4. 等待 DAG 執行完畢（約 1-2 分鐘）
5. 重新整理前端頁面 `http://localhost`，應顯示商品卡片與價格資料

> **注意**：如果前端顯示「No products tracked yet」，表示 DAG 尚未執行或執行失敗。請在 Airflow UI 確認 DAG run 狀態為 `success`。

### 6. 查看日誌

```bash
# 所有服務
docker compose logs -f

# 特定服務
docker compose logs -f api
docker compose logs -f airflow-scheduler
```

### 7. 停止服務

```bash
# 停止但保留資料
docker compose down

# 停止並清除資料（包含資料庫）
docker compose down -v
```

---

## API 端點說明

所有端點以 `/api/v1` 為前綴。


| 方法  | 路徑                      | 說明          | 查詢參數                                              |
| --- | ----------------------- | ----------- | ------------------------------------------------- |
| GET | `/health`               | 健康檢查        | —                                                 |
| GET | `/stats`                | 儀表板統計數據     | —                                                 |
| GET | `/products`             | 商品列表        | `search`, `page`, `page_size`, `sort_by`, `order` |
| GET | `/products/{id}`        | 商品詳情（含賣家資訊） | —                                                 |
| GET | `/products/{id}/prices` | 價格歷史（圖表用）   | `days`（預設 30）                                     |


### 排序參數

`sort_by` 支援：`updated_at`（預設）、`name`、`created_at`

`order` 支援：`desc`（預設）、`asc`

### 範例

```bash
# 搜尋商品
curl 'http://localhost:8000/api/v1/products?search=DDR5&page=1&page_size=10'

# 取得商品 #1 的 60 天價格歷史
curl 'http://localhost:8000/api/v1/products/1/prices?days=60'

# 儀表板統計
curl 'http://localhost:8000/api/v1/stats'
```

完整 Swagger 文件：`http://localhost:8000/docs`

---

## Airflow DAG 說明

### `pchome_price_scraper`（每 6 小時）

```
get_active_keywords → scrape_keyword (dynamic mapping) → upsert_products_and_prices → refresh_materialized_view → invalidate_cache
```

1. 從 `tracked_keywords` 表讀取活躍關鍵字
2. 對每個關鍵字呼叫 PChome v4.3 Search API（含 1-3 秒隨機延遲）
3. UPSERT 商品資料 + INSERT 價格歷史（單一 shop: PChome 24h）
4. 更新 Materialized View（`REFRESH MATERIALIZED VIEW CONCURRENTLY`）
5. 清除 Redis 快取

**PChome 價格邏輯**：

- 若商品有促銷價（`sale_price`）：`price = sale_price`，`original_price = 原始定價`
- 若無促銷：`price = 定價`，`original_price = NULL`

### `price_data_cleanup`（每日 02:00）

```
delete_old_price_history → delete_old_scrape_jobs → deactivate_stale_products → vacuum_tables → refresh_materialized_view
```

1. 刪除 90 天以上的價格歷史
2. 刪除 30 天以上的爬取任務紀錄
3. 將 14 天未更新的商品標記為不活躍
4. VACUUM ANALYZE 所有資料表
5. 重新整理 Materialized View

---

## E2E 測試

完整的端到端測試套件，涵蓋 DB → Airflow DAG → FastAPI → Frontend 的完整 pipeline。共 53 個測試案例。

### 測試架構

| 測試檔案 | 說明 | 測試數 |
| --- | --- | --- |
| `test_00_infrastructure` | 服務連通性（PostgreSQL、Redis、FastAPI、Airflow、Frontend） | 5 |
| `test_01_database` | Schema、seed data、materialized view、indexes 驗證 | 7 |
| `test_02_api` | 所有 REST API 端點（health、products、prices、stats） | 12 |
| `test_03_airflow_dags` | DAG metadata + 觸發執行 + DB 副作用驗證 | 11 |
| `test_04_frontend` | Playwright 瀏覽器測試（Header、HomePage、SearchPage、ProductDetailPage） | 17 |
| `test_05_full_pipeline` | 完整 E2E：DAG 觸發 → DB 寫入 → API 回傳 → Frontend 顯示 | 1 |

### 安裝測試依賴

```bash
pip install -r tests/requirements-test.txt
playwright install --with-deps chromium
```

### 執行測試

所有測試都需要先啟動相關服務（PostgreSQL、Redis、FastAPI、Airflow、Frontend）。

```bash
cd /workspace/price-tracker

# 執行全部測試
pytest tests/e2e/ -v --timeout=600

# 快速測試（不含 DAG 觸發和瀏覽器測試）
pytest tests/e2e/ -v -m "not slow and not frontend" --timeout=60

# 只跑 Airflow DAG 測試
pytest tests/e2e/test_03_airflow_dags.py -v --timeout=600

# 只跑 Playwright 瀏覽器測試
pytest tests/e2e/test_04_frontend.py -v

# 只跑完整 pipeline 測試
pytest tests/e2e/test_05_full_pipeline.py -v --timeout=600
```

### 測試標記

- `@pytest.mark.slow` — 需要觸發 DAG 執行的測試（較慢，需要網路）
- `@pytest.mark.frontend` — 需要 Playwright 瀏覽器的測試

### 環境變數

測試透過以下環境變數配置服務位址（皆有預設值）：

| 環境變數 | 預設值 | 說明 |
| --- | --- | --- |
| `API_URL` | `http://localhost:8000` | FastAPI 後端 |
| `FRONTEND_URL` | `http://localhost:5173` | Vite 前端開發伺服器 |
| `AIRFLOW_URL` | `http://localhost:8081` | Airflow API server |
| `DB_CONN` | `postgresql://pricetracker:pricetracker@localhost:5432/pricetracker` | PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis |

---

## 管理追蹤的關鍵字

透過 SQL 直接操作 `tracked_keywords` 表：

```bash
# 新增關鍵字
psql -d pricetracker -c "INSERT INTO tracked_keywords (keyword, max_pages) VALUES ('RTX 5090', 3);"

# 查看所有關鍵字
psql -d pricetracker -c "SELECT * FROM tracked_keywords;"

# 停用某個關鍵字
psql -d pricetracker -c "UPDATE tracked_keywords SET is_active = FALSE WHERE keyword = 'DDR4 記憶體';"

# 刪除關鍵字
psql -d pricetracker -c "DELETE FROM tracked_keywords WHERE keyword = 'RTX 5090';"
```

下次 DAG 執行時會自動讀取最新的關鍵字清單。

---

## 常見問題排除

### PostgreSQL 連線失敗

```bash
# 確認 PostgreSQL 正在運行
sudo pg_ctlcluster 15 main status

# 重新啟動
sudo pg_ctlcluster 15 main restart

# 確認認證模式（asyncpg 使用 TCP 連線）
cat /etc/postgresql/15/main/pg_hba.conf | grep -v "^#" | grep -v "^$"
```

如果 `psql` 能連但 API 報 `InvalidPasswordError`，是因為 asyncpg 使用 TCP 而非 Unix socket。請參考步驟 3 設定密碼或 trust 模式。

### Redis 連線失敗

API 可以在沒有 Redis 的情況下正常運行（快取失敗時會自動 fallback 到直接查詢 DB）。若需要快取：

```bash
# 確認 Redis 正在運行
redis-cli ping   # 應回傳 PONG

# 重新啟動
sudo redis-server --daemonize yes
```

### Airflow DAG 未出現

```bash
# 確認環境變數
echo $AIRFLOW_HOME                    # 應為 /workspace/price-tracker/airflow
echo $AIRFLOW__CORE__DAGS_FOLDER      # 應為 /workspace/price-tracker/airflow/dags

# 檢查 DAG 語法
source .venv/bin/activate
python3 airflow/dags/pchome_scraper_dag.py

# 重新序列化（如果 dags list 顯示空結果）
airflow dags reserialize
airflow dags list
```

### Airflow DAG 任務卡在 queued / 持續 retry

Airflow 3.x 的 LocalExecutor 會在子進程中透過 execution API 與 API server 通訊。如果 API server 不在預設的 port 8080，需要明確設定：

```bash
export AIRFLOW__CORE__EXECUTION_API_SERVER_URL="http://localhost:8081/execution/"
```

症狀：task 狀態停留在 `queued` 或 `up_for_retry`，scheduler log 出現 `Connection refused` 錯誤。

### 前端顯示「No products tracked yet」

1. **DAG 尚未執行**：首次啟動後需手動觸發 `pchome_price_scraper` DAG（見 Docker Compose 步驟 5）
2. **DAG 執行失敗**：在 Airflow UI (`http://localhost:8081`) 檢查 DAG run 狀態與 task logs

### 前端 API 請求失敗

```bash
# 確認後端正在運行
curl http://localhost:8000/api/v1/health

# Docker 模式：透過 Nginx 代理（前端使用相對路徑 /api/v1）
curl http://localhost/api/v1/health

# 開發模式：Vite proxy 將 /api 轉發到 localhost:8000
cat frontend/vite.config.ts
```

### PChome API 相關問題

PChome Search API 相對穩定，但仍可能遇到以下情況：

1. **回傳空結果**：某些關鍵字可能沒有搜尋結果，這是正常的
2. **請求過於頻繁**：增加延遲 — 修改 `.env` 中的 `SCRAPE_DELAY_MIN` / `SCRAPE_DELAY_MAX`
3. **DAG 執行時間長**：正常現象，每個關鍵字需要真實 HTTP 請求 + rate limiting 延遲
4. 檢查 Airflow 日誌中的詳細錯誤訊息

