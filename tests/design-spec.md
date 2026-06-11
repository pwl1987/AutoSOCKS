# 融媒体平台设计规格

> **项目名称**：media-platform（临沂融媒体中心）
> **日期**：2026-06-11
> **版本**：v1.3（锁定版）
> **团队**：1-2 人，全程 AI 辅助开发

---

## 1. 核心决策

| 决策 | 结论 |
|------|------|
| 架构模式 | 单体应用 + 模块化包（modular monolith） |
| 后台管理 | SQLAdmin 0.24+（Tabler UI，零前端代码） |
| 后端框架 | FastAPI + SQLAlchemy 2.0 异步 |
| 数据库 | PostgreSQL 15+ + pgvector ≥0.5.0（HNSW 索引） |
| 对象存储 | MinIO（Phase 0 仅实现 MinIO，不做 local 抽象） |
| 缓存/队列 | Redis + Celery（业务 DB0，Celery broker DB1，Celery result DB2） |
| 前端 | Full-Stack FastAPI Template（React），后续阶段 |
| AI 模型 | 复用第零阶段验证结果（MiniCPM-V/Qwen3-ASR/RapidOCR/InsightFace/PySceneDetect） |
| 项目位置 | Z:\media-platform |
| 开发顺序 | 全模块骨架优先，渐进式添加模型和迁移 |

---

## 2. 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│  Nginx（SSL/负载均衡/静态资源）                                   │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI 主应用（含 SQLAdmin）                                    │
│  ├── /api/v1/*          REST API（业务端点）                      │
│  ├── /admin/*           SQLAdmin 后台管理                        │
│  └── /docs              Swagger UI                               │
├─────────────────────────────────────────────────────────────────┤
│  独立服务（同机 Docker Compose，共享数据库）                       │
│  ├── celery_worker      转码、VMS 管线、备份（同步 DB 引擎）      │
│  ├── celery_beat        定时调度                                  │
│  ├── ai_server          AI 推理服务（GPU，HTTP API）              │
│  └── srs                流媒体（直播推流/录制）                    │
├─────────────────────────────────────────────────────────────────┤
│  基础设施                                                        │
│  ├── PostgreSQL + pgvector   ├── Redis (DB0业务/DB1/2 Celery)    │
│  └── MinIO                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 项目结构

```
Z:\media-platform\
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI 入口 + SQLAdmin 挂载
│   │   ├── config.py                   # Pydantic Settings
│   │   ├── database.py                 # 异步引擎 + 同步引擎（Celery 用）
│   │   ├── events.py                   # 事件分发（Pub/Sub 通知 + Celery 必达）
│   │   ├── models/                     # SQLAlchemy 模型
│   │   │   ├── __init__.py             # 显式导出所有模型
│   │   │   ├── base.py                 # 基类：BIGINT id + UUID + 时区感知时间戳
│   │   │   ├── system.py               # User / Role / Permission / AuditLog
│   │   │   ├── site.py                 # Site
│   │   │   ├── cms.py                  # Content / Taxonomy / Comment / Tag
│   │   │   ├── media.py                # MediaAsset / MediaTag / MediaSegment / MediaDownload
│   │   │   ├── vms.py                  # VMSVideo / Shot / Keyframe / Person / FaceEmbedding / ProcessingLog
│   │   │   ├── capture.py              # CaptureSource / CaptureRoute / CaptureTask
│   │   │   ├── quality.py              # QualityReport
│   │   │   ├── live.py                 # LiveChannel / LiveRecord / BroadcastEPG
│   │   │   ├── member.py               # Member / MemberLevel / PointsLog / WatchHistory
│   │   │   ├── ai.py                   # AITask / AIModel / Subtitle / ModerationResult
│   │   │   ├── workflow.py             # ReviewFlow / ReviewNode / ReviewRecord
│   │   │   ├── stats.py                # BillingRecord / BillingPricing / BackupRecord / ReportTemplate
│   │   │   └── sync.py                 # SyncChannel / SyncRule / SyncLog
│   │   ├── admin/                      # SQLAdmin 视图
│   │   │   ├── __init__.py             # register_admin_views(admin)
│   │   │   ├── auth.py                 # 环境变量凭证认证
│   │   │   └── views/                  # 按模块分文件
│   │   │       ├── system_admin.py
│   │   │       ├── cms_admin.py
│   │   │       ├── media_admin.py
│   │   │       ├── vms_admin.py
│   │   │       ├── live_admin.py
│   │   │       ├── member_admin.py
│   │   │       ├── ai_admin.py
│   │   │       ├── workflow_admin.py
│   │   │       ├── stats_admin.py
│   │   │       └── dashboard_view.py   # 自定义仪表盘（BaseView）
│   │   ├── api/v1/                     # REST API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── sites.py
│   │   │   ├── content.py
│   │   │   ├── media.py
│   │   │   ├── vms.py
│   │   │   ├── live.py
│   │   │   ├── member.py
│   │   │   ├── ai.py
│   │   │   ├── capture.py
│   │   │   └── workflow.py
│   │   ├── schemas/                    # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── response.py            # 统一响应格式 Response / PageResponse
│   │   │   ├── pagination.py          # PageParams
│   │   │   └── ...                     # 按模块分文件
│   │   ├── services/                   # 业务逻辑层（仅异步，不被 Celery 导入）
│   │   ├── tasks/                      # Celery 异步任务（使用同步 DB 引擎）
│   │   │   ├── __init__.py             # Celery app 配置 + 队列定义
│   │   │   ├── transcode.py            # @celery_app.task(queue="cpu")
│   │   │   ├── vms_pipeline.py         # @celery_app.task(queue="gpu")
│   │   │   ├── backup.py               # @celery_app.task(queue="io")
│   │   │   └── sync.py
│   │   └── utils/                      # 工具函数
│   │       ├── storage.py              # MinIO 封装
│   │       └── inference.py            # AI 推理客户端
│   ├── templates/sqladmin/             # SQLAdmin 模板覆盖
│   ├── static/                         # 自定义 CSS/JS
│   ├── alembic/                        # 数据库迁移
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                           # React 前台（后续阶段）
├── docker-compose.yml
├── docker-compose.gpu.yml              # GPU 服务覆盖
├── .env.example
├── nginx/nginx.conf
├── scripts/
│   ├── init_db.sql
│   └── verify_p0.sh
└── docs/
```

---

## 4. 模型设计

### 4.1 base.py — 模型基类

```python
from sqlalchemy import Column, BigInteger, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase
import uuid

class Base(DeclarativeBase):
    pass

class BaseModel(Base):
    """所有模型的基类。

    主键策略：BIGINT 自增做内部关联（紧凑、高性能），
    UUID 做对外暴露标识符（API 路径、跨系统引用）。

    软删除：使用 deleted_at 时间戳（非布尔），支持：
    - PostgreSQL 部分唯一索引：CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL
    - 查询时过滤：WHERE deleted_at IS NULL
    - 记录删除时间

    时间戳：使用 server_default=func.now() 让数据库生成时区感知时间，
    避免Python端 datetime.utcnow 的时区混乱。
    """
    __abstract__ = True
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # NULL=未删除
```

### 4.2 外键级联策略约定

| 场景 | 策略 | 示例 |
|------|------|------|
| 强依赖（子记录无意义） | `CASCADE` | VMSVideo → MediaAsset（媒资删则分析删） |
| 可独立存在 | `SET NULL` | AuditLog.user_id → User（用户删但审计保留） |
| 默认 | `RESTRICT` | 防止误删，需显式处理 |

```python
# 强依赖示例
media_asset_id = Column(BigInteger, ForeignKey("media_asset.id", ondelete="CASCADE"), nullable=False)
# 审计保留示例
user_id = Column(BigInteger, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
```

### 4.3 模型清单（12 个文件）

| 文件 | __tablename__ | 模型 | 说明 |
|------|---------------|------|------|
| system.py | user, role, permission, audit_log | User, Role, Permission, AuditLog | 用户/权限/审计 |
| site.py | site | Site | 多站点 |
| cms.py | content, taxonomy, comment, tag | Content, Taxonomy, Comment, Tag | 内容管理 |
| media.py | media_asset, media_tag, media_segment, media_download | MediaAsset, MediaTag, MediaSegment, MediaDownload | 媒资管理 |
| vms.py | vms_video, vms_shot, vms_keyframe, vms_person, vms_face_embedding, vms_processing_log | VMSVideo, Shot, Keyframe, Person, FaceEmbedding, ProcessingLog | 视频结构化 |
| capture.py | capture_source, capture_route, capture_task | CaptureSource, CaptureRoute, CaptureTask | 收录管理 |
| quality.py | quality_report | QualityReport | 质量检测 |
| live.py | live_channel, live_record, broadcast_epg | LiveChannel, LiveRecord, BroadcastEPG | 直播 |
| member.py | member, member_level, points_log, watch_history | Member, MemberLevel, PointsLog, WatchHistory | 会员 |
| ai.py | ai_task, ai_model, subtitle, moderation_result | AITask, AIModel, Subtitle, ModerationResult | AI 能力 |
| workflow.py | review_flow, review_node, review_record | ReviewFlow, ReviewNode, ReviewRecord | 审核工作流 |
| stats.py | billing_record, billing_pricing, backup_record, report_template | BillingRecord, BillingPricing, BackupRecord, ReportTemplate | 统计/报表 |
| sync.py | sync_channel, sync_rule, sync_log | SyncChannel, SyncRule, SyncLog | 多端分发 |

### 4.4 ProcessingLog 字段定义

```python
class ProcessingLog(BaseModel):
    __tablename__ = "vms_processing_log"
    vms_video_id = Column(BigInteger, ForeignKey("vms_video.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(30), nullable=False)      # split_shots / run_asr / run_ocr / ...
    status = Column(String(20), nullable=False)     # pending / running / completed / failed
    message = Column(Text, nullable=True)           # 错误信息或备注
    detail = Column(JSONB, nullable=True)            # 结构化详情
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

### 4.5 VMS 与 MediaAsset 关系

```python
class VMSVideo(BaseModel):
    __tablename__ = "vms_video"
    media_asset_id = Column(BigInteger, ForeignKey("media_asset.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(20), default="v1")      # 支持重新分析
    processing_stage = Column(String(30))
    processing_state = Column(JSONB)                 # 需导入: from sqlalchemy.dialects.postgresql import JSONB
    duration_ms = Column(BigInteger)
    width = Column(Integer)
    height = Column(Integer)
    fps = Column(Float)
    codec = Column(String(50))
    asr_full_text = Column(Text)
```

---

## 5. 统一 API 规范

### 5.1 统一响应格式

```python
# schemas/response.py
from typing import Any, Optional, List, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Response(BaseModel):
    """统一响应格式"""
    code: int = 0
    message: str = "success"
    data: Any = None

class PageResponse(BaseModel):
    """统一分页响应"""
    code: int = 0
    message: str = "success"
    data: List[Any] = []
    total: int = 0
    page: int = 1
    size: int = 20
```

### 5.2 分页请求参数

```python
# schemas/pagination.py
from pydantic import BaseModel, Field

class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
```

### 5.3 业务错误码范围

| 范围 | 模块 |
|------|------|
| 1000-1999 | 通用错误（参数校验、权限、系统） |
| 2000-2999 | 认证错误（登录、Token、MFA） |
| 3000-3999 | 媒资/VMS 错误（上传、转码、处理管线） |
| 4000-4999 | AI 服务错误（推理超时、模型不可用） |
| 5000-5999 | 直播错误（推流、信号） |

---

## 6. 关键技术决策

### 6.1 Celery 数据库会话（严格隔离）

Celery worker 使用**同步引擎**，且**不导入** `services/` 中的异步服务层：

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# FastAPI 用
async_engine = create_async_engine(DATABASE_URL)  # postgresql+asyncpg://
AsyncSession = async_sessionmaker(async_engine)

# Celery 用（独立引擎，同步）
sync_engine = create_engine(SYNC_DATABASE_URL)  # postgresql+psycopg2://
SyncSession = sessionmaker(sync_engine)
```

**规则**：`tasks/` 目录内的代码只使用 `SyncSession`，不导入 `services/` 中的异步代码。

### 6.2 Celery 队列分配规则

```python
# tasks/__init__.py
from celery import Celery

celery_app = Celery("media_platform", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# 队列定义
# - cpu: CPU 密集（镜头切分、关键帧抽取、备份）
# - gpu: GPU 密集（ASR、OCR、人脸检测、转码）
# - io:  IO 密集（MinIO 操作、同步分发）

# 任务分配示例
@celery_app.task(queue="cpu")
def split_shots(video_id: int): ...

@celery_app.task(queue="gpu")
def run_asr(video_id: int): ...

@celery_app.task(queue="io")
def backup_database(): ...
```

### 6.3 Redis DB 分工

| DB | 用途 | 配置变量 |
|----|------|----------|
| 0 | 业务缓存 + Pub/Sub 通知 | `REDIS_URL` |
| 1 | Celery broker | `CELERY_BROKER_URL` |
| 2 | Celery result backend | `CELERY_RESULT_BACKEND` |

`events.py` 中的 Pub/Sub 使用 `REDIS_URL`（DB0），与 Celery 完全隔离。

### 6.4 事件分发（两种机制）

| 场景 | 机制 | 示例 |
|------|------|------|
| 可丢失通知 | Redis Pub/Sub（DB0） | 刷新缓存、UI 实时更新（SSE） |
| 必达事件 | Celery 任务 | 审核完成触发分发、内容发布触发同步 |

```python
# events.py
import redis.asyncio as aioredis
from app.config import settings

# 可丢失：Pub/Sub（使用 DB0）
async def notify(event_type: str, payload: dict):
    """即发即弃，订阅者不在线则消息丢失"""
    r = aioredis.from_url(settings.REDIS_URL)
    await r.publish(f"notify:{event_type}", json.dumps(payload))

# 必达：Celery 任务
def dispatch(task_name: str, **kwargs):
    """通过 Celery 确保执行"""
    from app.tasks import celery_app
    celery_app.send_task(task_name, kwargs=kwargs)
```

### 6.5 SQLAdmin 认证

使用**环境变量凭证**，不查业务用户表：

```python
# admin/auth.py
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.config import settings

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if (form.get("username") == settings.ADMIN_USERNAME and
            form.get("password") == settings.ADMIN_PASSWORD):
            request.session.update({"authenticated": True})
            return True
        return False

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
```

### 6.6 SQLAdmin 钩子规则

ModelView 的 `on_model_change` 等钩子**只做同步校验**，需要异步操作时发 Celery 任务：

```python
from sqladmin.exceptions import ValidationError

class ContentAdmin(ModelView, model=Content):
    async def on_model_change(self, data, model, is_created):
        # 只做同步校验
        if not model.title:
            raise ValidationError("标题不能为空")
        # 异步工作交给 Celery
        dispatch("tasks.sync.dispatch_content", content_id=model.id)
```

### 6.7 pgvector 索引

确保 pgvector ≥0.5.0，HNSW 索引在建表迁移中创建，索引名与 `__tablename__` 一致：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
-- vms_keyframe 表（Keyframe 模型）
CREATE INDEX idx_vms_keyframe_embedding ON vms_keyframe
    USING hnsw (embedding vector_cosine_ops);
-- media_segment 表（MediaSegment 模型）
CREATE INDEX idx_media_segment_embedding ON media_segment
    USING hnsw (embedding vector_cosine_ops);
```

### 6.8 存储层（S3 兼容）

使用 `aiobotocore` 统一 S3 客户端，开发用 MinIO，生产可无缝切换任意 S3 兼容存储（阿里云 OSS/华为云 OBS/Ceph），国产化零改动：

```python
# utils/storage.py
import aiobotocore.session

class Storage:
    def __init__(self):
        session = aiobotocore.session.get_session()
        self._session = session

    async def _get_client(self):
        return self._session.create_client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,        # http://minio:9000
            aws_access_key_id=settings.S3_ACCESS_KEY,  # minioadmin
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    async def upload(self, bucket: str, key: str, data: bytes) -> str: ...
    async def download(self, bucket: str, key: str) -> bytes: ...
    async def get_presigned_url(self, bucket: str, key: str, expires: int = 3600) -> str: ...
```

### 6.9 国产化兼容

| 组件 | 当前方案 | 国产替代 | 改动量 |
|------|---------|----------|--------|
| 对象存储 | MinIO (S3) | 任何 S3 兼容产品 | 零（换 endpoint） |
| 缓存/队列 | Redis | Valkey（完全兼容） | 零（换镜像） |
| 数据库 | PostgreSQL | 人大金仓/瀚高（兼容协议） | 极小（换连接串） |
| AI 推理 | 自建容器 | 国产 GPU + 国产模型 | 无（模型可换） |

Redis 替换 Valkey 只需改镜像：`valkey/valkey:8-alpine` 替代 `redis:7-alpine`，代码零改动。

---

## 7. 环境变量

```bash
# .env.example

# 数据库
DATABASE_URL=postgresql+asyncpg://media:media123@postgres:5432/media
SYNC_DATABASE_URL=postgresql+psycopg2://media:media123@postgres:5432/media

# Redis（业务缓存 + Pub/Sub）
REDIS_URL=redis://redis:6379/0

# Celery（独立 DB，与业务隔离）
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_CONCURRENCY=4

# S3 兼容存储（MinIO / 阿里云 OSS / 华为云 OBS）
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_REGION=us-east-1

# AI 推理服务
AI_SERVICE_URL=http://ai_server:8001

# SQLAdmin 管理凭证（独立于业务用户）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123

# JWT（业务 API 认证）
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

---

## 8. 部署拓扑

```yaml
# docker-compose.yml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]
    env_file: .env

  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker -Q cpu,gpu,io -c ${CELERY_CONCURRENCY:-4} -l info
    depends_on: [postgres, redis, minio]
    env_file: .env

  celery_beat:
    build: ./backend
    command: celery -A app.tasks beat -l info
    depends_on: [redis]
    env_file: .env

  postgres:
    image: pgvector/pgvector:pg15
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: media
      POSTGRES_USER: media
      POSTGRES_PASSWORD: media123

  redis:
    image: redis:7-alpine
    volumes: [redisdata:/data]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123

volumes:
  pgdata:
  redisdata:
  miniodata:
```

GPU 覆盖（`docker-compose.gpu.yml`）：

```yaml
services:
  celery_worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  ai_server:
    build: ./ai-service
    ports: ["8001:8001"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 9. 开发路线图

| 周 | 交付 |
|----|------|
| **第 0 周** | Docker Compose 启动 → 基础模型（User/Site）→ 第一次 Alembic 迁移 → SQLAdmin 可访问 → 能管理 User 和 Site |
| **第 0 周末** | 验证后台能查看/编辑 User 和 Site 表 |
| **第 1 周** | 添加 Content/MediaAsset 模型 + 迁移 + SQLAdmin 视图 + 视频上传 API（分片→MinIO） |
| **第 2 周** | Celery 配置 + 转码任务（FFmpeg）+ VMS 管线骨架（Shot/Keyframe 模型） |
| **第 3 周** | AI 推理服务容器 + 字幕/标签生成集成 |
| **第 4 周** | Live/Member/Workflow 模型 + 迁移 + SQLAdmin 视图 + API 骨架 |
| **第 5 周+** | 前端（React）+ 其他模块业务逻辑填充 |

**原则**：每次只添加 1-2 个模型，立即做迁移验证，避免一次性生成所有模型。

---

## 10. API 路由规划

| 模块 | 路由前缀 | 模型文件 | 核心端点 |
|------|----------|----------|----------|
| 系统 | /api/v1/system | system.py | users, roles, permissions, audit-logs |
| 站点 | /api/v1/sites | site.py | CRUD |
| CMS | /api/v1/content | cms.py | CRUD + cross-post + comments |
| 媒资 | /api/v1/media | media.py | upload, list, detail, search, download |
| VMS | /api/v1/vms | vms.py | videos, shots, asr, ocr, faces, events(SSE) |
| 收录 | /api/v1/capture | capture.py | sources, routes, tasks |
| 直播 | /api/v1/live | live.py | channels, records, epg |
| 会员 | /api/v1/member | member.py | register, login, profile, points, history |
| AI | /api/v1/ai | ai.py | subtitles, moderation, tags, tasks |
| 工作流 | /api/v1/workflow | workflow.py | flows, records |
| 统计 | /api/v1/stats | stats.py | dashboard, billing, backup |
| 同步 | /api/v1/sync | sync.py | channels, rules, logs |

---

## 11. 审查修订记录

| 日期 | 版本 | 修订内容 |
|------|------|----------|
| 2026-06-11 | v1.0 | 初始版本 |
| 2026-06-11 | v1.1 | BIGINT+UUID 主键 / deleted_at 软删除 / SQLAdmin 环境变量认证 / Celery 严格隔离 / 双事件机制 / Phase 0 仅 MinIO / 模型文件独立 / 渐进式迁移 |
| 2026-06-11 | v1.2 | 时区感知时间戳(func.now()) / 外键 ondelete 策略 / ProcessingLog 完整定义 / 表名与模型名统一 / ValidationError 导入 / Celery 队列分配规则 / Redis DB 分工 / 统一响应格式+分页Schema+错误码 / JSONB 导入路径 |
| 2026-06-11 | v1.3 | 存储层改用 aiobotocore(S3兼容) / 国产化兼容表(Valkey/人大金仓) / Celery 并发数环境变量 / AI server healthcheck / 锁定版 |
