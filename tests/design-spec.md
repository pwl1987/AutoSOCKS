# 融媒体平台设计规格

> **项目名称**：media-platform（临沂融媒体中心）
> **日期**：2026-06-11
> **版本**：v2.0（最终锁定版）
> **团队**：1-2 人，全程 AI 辅助开发

---

## 1. 核心决策

| 决策 | 结论 |
|------|------|
| 架构模式 | 单体应用 + 模块化包（modular monolith） |
| 后台管理 | SQLAdmin >=0.27,<0.28（Tabler UI，零前端代码） |
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

> **软删除与级联的关系**：`ondelete="CASCADE"` 仅在硬删除（`DELETE FROM`）时由数据库触发；日常软删除（`UPDATE deleted_at`）时，CASCADE **不会触发**。因此必须在业务层（Service / Celery Task）软删除主表时，批量软删除子表。例如：软删除 MediaAsset 时，必须同时设置 VMSVideo / TranscodeTask 等子表的 `deleted_at`。
>
> | 策略 | 触发时机 | 说明 |
> |------|---------|------|
> | `ondelete="CASCADE"` | 硬删除（DELETE FROM） | 数据库层面级联删除子表 |
> | 业务层软删除级联 | 软删除（UPDATE deleted_at） | Service 层批量更新子表 `deleted_at` |

### 4.3 模型清单（13 个文件）

| 文件 | __tablename__ | 模型 | 说明 |
|------|---------------|------|------|
| system.py | user, role, permission, audit_log | User, Role, Permission, AuditLog | 用户/权限/审计 |
| site.py | site | Site | 多站点 |
| cms.py | content, taxonomy, comment, tag | Content, Taxonomy, Comment, Tag | 内容管理 |
| media.py | media_asset, media_tag, media_segment, media_download, transcode_preset, media_upload_session | MediaAsset, MediaTag, MediaSegment, MediaDownload, TranscodePreset, MediaUploadSession | 媒资管理 + 转码预设 + 上传会话 |
| vms.py | vms_video, vms_shot, vms_keyframe, vms_person, vms_face_embedding, vms_processing_log | VMSVideo, Shot, Keyframe, Person, FaceEmbedding, ProcessingLog | 视频结构化 |
| capture.py | capture_source, capture_route, capture_task | CaptureSource, CaptureRoute, CaptureTask | 收录管理 |
| quality.py | quality_report | QualityReport | 质量检测 |
| live.py | live_channel, live_record, broadcast_epg | LiveChannel, LiveRecord, BroadcastEPG | 直播 |
| member.py | member, member_level, points_log, watch_history | Member, MemberLevel, PointsLog, WatchHistory | 会员 |
| ai.py | ai_task, ai_model, subtitle, moderation_result | AITask, AIModel, Subtitle, ModerationResult | AI 能力（含 model_version 追溯） |
| workflow.py | review_flow, review_node, review_record, sensitive_word | ReviewFlow, ReviewNode, ReviewRecord, SensitiveWord | 审核工作流 + 敏感词库 |
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

### 4.5 转码预设模型

```python
class TranscodePreset(BaseModel):
    __tablename__ = "transcode_preset"
    name = Column(String(100), nullable=False, unique=True)   # "1080p_hls", "720p_mp4"
    container = Column(String(20))                             # hls / mp4 / webm
    resolution = Column(String(20))                            # 1920x1080, 1280x720
    video_codec = Column(String(20), default="h264")           # h264 / h265 / vp9
    video_bitrate = Column(String(20))                         # "5000k"
    audio_codec = Column(String(20), default="aac")
    audio_bitrate = Column(String(20), default="128k")
    extra_params = Column(JSONB)                               # FFmpeg 额外参数
    is_enabled = Column(Boolean, default=True)
```

### 4.6 敏感词库模型

```python
class SensitiveWord(BaseModel):
    __tablename__ = "sensitive_word"
    word = Column(String(200), nullable=False, unique=True)
    category = Column(String(50))       # political / porn / violence / custom
    level = Column(Integer, default=1)  # 1=低 2=中 3=高
    source = Column(String(50))         # manual / imported / system
    is_enabled = Column(Boolean, default=True)
```

### 4.6 VMS 与 MediaAsset 关系

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

### 4.9 关联表（多对多）

```python
# system.py
role_permission = Table(
    "role_permission", Base.metadata,
    Column("role_id", BigInteger, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
)

# cms.py
content_tag = Table(
    "content_tag", Base.metadata,
    Column("content_id", BigInteger, ForeignKey("content.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", BigInteger, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)
```

### 4.10 MediaAsset 文件元数据

```python
class MediaAsset(BaseModel):
    __tablename__ = "media_asset"
    filename = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)          # 字节
    mime_type = Column(String(100), nullable=False)         # video/mp4
    checksum_sha256 = Column(String(64), nullable=False)    # 完整性校验
    storage_bucket = Column(String(100), nullable=False)    # S3 bucket
    storage_key = Column(String(500), nullable=False)       # S3 object key
    storage_etag = Column(String(100))                      # S3 ETag
    duration_ms = Column(BigInteger)                        # 音视频时长
    width = Column(Integer)                                 # 视频宽
    height = Column(Integer)                                # 视频高
    bitrate = Column(Integer)                               # 码率
    site_id = Column(BigInteger, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False)
    source_media_asset_id = Column(BigInteger, ForeignKey("media_asset.id", ondelete="SET NULL"), nullable=True, comment="原画资产ID，为空代表是原画或非视频文件")
    media_type = Column(String(50))                         # video/audio/image/document
    transcode_status = Column(String(20), default="pending") # pending/processing/ready/failed
```

### 4.11 分片上传会话

```python
class MediaUploadSession(BaseModel):
    __tablename__ = "media_upload_session"
    media_asset_id = Column(BigInteger, ForeignKey("media_asset.id", ondelete="CASCADE"))
    total_parts = Column(Integer, nullable=False)
    uploaded_parts = Column(JSONB, default=list)            # [1, 2, 3, ...]
    part_size = Column(BigInteger, nullable=False)          # 如 10MB
    status = Column(String(20), default="pending")          # pending/uploading/completed/aborted
    expires_at = Column(DateTime(timezone=True))            # 24h 过期清理
```

### 4.12 标识符使用约定

| 场景 | 标识符 | 示例 |
|------|--------|------|
| 数据库内部关联/外键 | BIGINT `id` | `media_asset_id = Column(BigInteger, ForeignKey(...))` |
| API 路径参数 | UUID `uuid` | `GET /api/v1/media/{uuid}` |
| 前端展示/分享链接 | UUID | `https://example.com/videos/a1b2c3d4-...` |
| 跨系统引用 | UUID | webhook 回调、分发目标 |

```python
# API 路由示例 — 路径参数统一使用 UUID
@router.get("/media/{uuid}")
async def get_media(uuid: UUID): ...
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

### 5.4 健康检查端点

```python
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready(db=Depends(get_db)):
    # 检查数据库连接、Redis、MinIO 等依赖
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
```

### 5.5 API 限流

使用 `slowapi` 防止突发请求打挂系统：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/media/upload/presign")
@limiter.limit("10/minute")
async def presign_upload(request: Request): ...
```

### 5.6 全局请求 ID

每个请求注入 `X-Request-ID`，便于日志排查：

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

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
async_engine = create_async_engine(
    DATABASE_URL,  # postgresql+asyncpg://
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
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

# 全局任务超时和安全配置
celery_app.conf.update(
    task_time_limit=30 * 60,            # 30 分钟硬超时
    task_soft_time_limit=25 * 60,       # 25 分钟软超时（触发异常）
    task_acks_late=True,                # 任务完成后才确认
    task_reject_on_worker_lost=True,    # Worker 崩溃时重新入队
    result_expires=86400,                # 任务结果 24h 过期，防止 Redis 堆积
    worker_prefetch_multiplier=1,        # 每次只取一个任务，避免堆积
    task_track_started=True,             # 跟踪任务开始状态
)

# 队列定义
# - cpu: CPU 密集（镜头切分、关键帧抽取、备份）
# - gpu: GPU 密集（ASR、OCR、人脸检测、向量嵌入）
# - video: 视频转码（FFmpeg，CPU 或 NVENC）
# - io:  IO 密集（MinIO 操作、同步分发）

# 任务分配示例
@celery_app.task(queue="cpu")
def split_shots(video_id: int): ...

@celery_app.task(queue="gpu")
def run_asr(video_id: int): ...

@celery_app.task(queue="video")
def transcode(media_asset_id: int, preset_id: int): ...

@celery_app.task(queue="io")
def backup_database(): ...
```

### 6.2.2 Celery Beat 定时任务

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cleanup-expired-uploads": {
        "task": "tasks.cleanup_expired_uploads",
        "schedule": crontab(hour="*/6"),
        # 清理时必须先 abort MinIO 分片 / delete 孤儿文件，再删除 DB 记录
    },       # 每 6 小时清理过期上传会话
    },
    "backup-database": {
        "task": "tasks.backup_database",
        "schedule": crontab(hour=2, minute=0),     # 每天凌晨 2 点备份
    },
}
```

### 6.2.1 VMS 任务重试策略

AI 推理任务（ASR/OCR/人脸检测）可能因 GPU OOM 或超时失败，需要自动重试：

```python
@celery_app.task(
    queue="gpu",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 指数退避：60s → 120s → 240s
    autoretry_for=(TimeoutError, ConnectionError),
)
def run_asr(self, video_id: int):
    try:
        ...
    except (TimeoutError, ConnectionError) as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
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

确保 pgvector ≥0.5.0，模型中明确声明向量维度，HNSW 索引在建表迁移中创建：

```python
# 模型中明确维度
from pgvector.sqlalchemy import Vector

class Keyframe(BaseModel):
    embedding = Column(Vector(768))   # MiniCPM-V 输出维度

class MediaSegment(BaseModel):
    embedding = Column(Vector(768))   # BGE 输出维度
```

```sql
-- 索引与 __tablename__ 一致
CREATE INDEX idx_vms_keyframe_embedding ON vms_keyframe
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_media_segment_embedding ON media_segment
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

查询时 `ef_search` 策略：默认 80（平衡），高召回检索 150，批量标注可降低至 40。

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
    async def get_presigned_upload_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        """生成预签名上传 URL，前端直传 MinIO/S3，不经过后端"""
        ...
    async def create_multipart_upload(self, bucket: str, key: str) -> str:
        """初始化分片上传，返回 upload_id"""
        ...
    async def upload_part(self, bucket: str, key: str, upload_id: str, part_number: int, data: bytes) -> str:
        """上传单个分片，返回 ETag"""
        ...
    async def complete_multipart_upload(self, bucket: str, key: str, upload_id: str, parts: list) -> None:
        """完成分片上传，合并所有分片"""
        ...
    async def ensure_bucket(self, bucket_name: str) -> None:
        """确保桶存在，不存在则创建，并配置 CORS（前端直传必需）"""
        try:
            await self.client.head_bucket(Bucket=bucket_name)
        except ClientError:
            await self.client.create_bucket(Bucket=bucket_name)
        # 配置 CORS（前端直传 MinIO 必需，否则浏览器拦截）
        cors_config = {
            "CORSRules": [{
                "AllowedOrigins": ["*"],  # 生产环境改为前端域名
                "AllowedMethods": ["GET", "PUT", "POST"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"]
            }]
        }
        await self.client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
```

**必须创建的桶**：`media-assets`、`hls`、`covers`、`vms-keyframes`。在 `main.py` 启动事件中调用 `storage.ensure_bucket()`。
```

**前端直传流程**（大文件必须直传，减轻后端压力）：
1. 前端请求 `POST /api/v1/media/upload/presign` → 后端返回预签名 URL
2. 前端直接 `PUT` 到预签名 URL → 文件进入 MinIO/S3
3. 前端通知 `POST /api/v1/media/upload/confirm` → 后端创建 MediaAsset 记录

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

# S3 兼容存储
S3_INTERNAL_ENDPOINT=http://minio:9000        # 容器内部访问
S3_PUBLIC_ENDPOINT=http://localhost:9000       # 前端/浏览器访问（Presigned URL）
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

# 时区
TZ=Asia/Shanghai
```

---

## 8. 部署拓扑

```yaml
# docker-compose.yml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    env_file: .env
    entrypoint: ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker -Q cpu,io,video -c 4 -l info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file: .env

  celery_worker_gpu:
    build: ./backend
    command: celery -A app.tasks worker -Q gpu -c 1 -l info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file: .env

  celery_beat:
    build: ./backend
    command: celery -A app.tasks beat -l info
    depends_on:
      redis:
        condition: service_healthy

  # Celery 任务监控（开发调试用）
  flower:
    build: ./backend
    command: celery -A app.tasks flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      redis:
        condition: service_healthy
    env_file: .env

  postgres:
    image: pgvector/pgvector:pg15
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: media
      POSTGRES_USER: media
      POSTGRES_PASSWORD: media123
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U media -d media"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes: [redisdata:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5

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

## 11. 权限码规范

```
# CMS 权限
content:create / content:update / content:review / content:publish / content:delete
# 媒资权限
media:upload / media:download / media:manage
# VMS 权限
vms:analyze / vms:view
# AI 权限
ai:task:create / ai:model:manage
# 直播权限
live:channel:manage / live:broadcast
# 系统权限
system:user:manage / system:role:manage / system:config / system:audit
```

---

## 12. 多站点数据隔离规则

| 模型 | 必须带 site_id | 说明 |
|------|---------------|------|
| Content | 是 | 每篇文章属于一个站点 |
| Taxonomy | 是 | 分类按站点隔离 |
| MediaAsset | 是 | 素材按站点隔离 |
| LiveChannel | 是 | 频道按站点隔离 |
| Member | 是 | 会员按站点隔离 |
| ReviewFlow | 是 | 审核流程按站点隔离 |
| SyncRule | 是 | 分发规则按站点 |
| User | 否 | 系统级，可跨站点 |
| Role | 否 | 系统级 |
| Permission | 否 | 系统级 |
| AuditLog | 可选 | 记录 site_id 但可为空（系统操作无站点） |

---

## 13. 内容生命周期状态机

```
draft → submitted → reviewing → approved → published
                                    ↓           ↓
                                 rejected    archived
                                    ↓
                              (修改后重新提交)

任何状态 → deleted（软删除，deleted_at 不为空）
```

字段：`Content.status` 取值：`draft / submitted / reviewing / rejected / approved / scheduled / published / archived`

```python
# 状态机强制校验（services/ 层）
VALID_TRANSITIONS = {
    "draft": ["submitted", "deleted"],
    "submitted": ["reviewing", "draft"],
    "reviewing": ["approved", "rejected"],
    "approved": ["scheduled", "published"],
    "rejected": ["draft"],
    "scheduled": ["published"],
    "published": ["archived"],
    "archived": ["draft"],
}
# API 层必须校验：if new_status not in VALID_TRANSITIONS.get(old_status, []): raise
```

---

## 14. AI 服务 API 契约

AI 推理服务（`ai_server`）统一接口规范：

| 端点 | 方法 | 输入 | 输出 | 超时 |
|------|------|------|------|------|
| `/v1/asr` | POST | `{video_url, language}` | `{task_id, segments: [{start, end, text}]}` | 300s |
| `/v1/ocr` | POST | `{image_url}` | `{texts: [{text, bbox, confidence}]}` | 30s |
| `/v1/face/detect` | POST | `{image_url}` | `{faces: [{bbox, confidence, embedding}]}` | 30s |
| `/v1/face/embed` | POST | `{image_url, face_bbox}` | `{embedding: [float]}` | 10s |
| `/v1/video/scene-detect` | POST | `{video_url, threshold}` | `{scenes: [{start, end}]}` | 120s |
| `/v1/embed` | POST | `{text or image_url}` | `{embedding: [float], dim: int}` | 10s |
| `/health` | GET | — | `{status: "ok", gpu_available: bool}` | 5s |
| `/models` | GET | — | `{models: [{name, version, status}]}` | 5s |

错误码：`model_unavailable / gpu_oom / invalid_media / timeout / internal_error`

输入统一使用 **MinIO presigned URL**（不在请求体传文件）。

---

## 15. Phase 0 验收清单

```
[ ] docker compose up 成功，所有服务 healthy
[ ] /docs 可访问（Swagger UI）
[ ] /admin 可登录（环境变量凭证）
[ ] User / Site 表可在 SQLAdmin 中增删改查
[ ] Alembic 能 upgrade / downgrade
[ ] MinIO bucket（media-assets, hls, covers, vms-keyframes）自动初始化
[ ] Celery worker 能执行 ping task
[ ] Redis DB0/DB1/DB2 分工验证（业务缓存 / broker / result 各自独立）
[ ] 上传一个测试视频到 MinIO（通过 presigned URL）
[ ] 创建 MediaAsset 记录
[ ] /health 返回 ok，/ready 检查依赖通过
[ ] 种子数据已初始化（超级管理员角色/用户/权限）
[ ] verify_p0.sh 全部通过
```

### 15.1 种子数据

`scripts/init_seed.py` 在首次部署时运行，插入初始数据：

- 角色：超级管理员（super_admin）、站点管理员（site_admin）、编辑（editor）、审核员（reviewer）
- 权限：按权限码规范批量插入
- 默认管理员用户：`admin` / 密码哈希（bcrypt）
- 默认站点：`main`（主站）

### 15.2 核心依赖

```txt
# requirements.txt 核心依赖
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30
sqlalchemy[asyncio]>=2.0
asyncpg>=0.30
psycopg2-binary>=2.9
alembic>=1.13
sqladmin>=0.27,<0.28
pydantic-settings>=2.0
celery[redis]>=5.4
redis>=5.0
aiobotocore>=2.15
pgvector>=0.3
slowapi>=0.1.9
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
httpx>=0.27
```

---

## 16. 审查修订记录

| 日期 | 版本 | 修订内容 |
|------|------|----------|
| 2026-06-11 | v1.0 | 初始版本 |
| 2026-06-11 | v1.1 | BIGINT+UUID 主键 / deleted_at 软删除 / SQLAdmin 环境变量认证 / Celery 严格隔离 / 双事件机制 / Phase 0 仅 MinIO / 模型文件独立 / 渐进式迁移 |
| 2026-06-11 | v1.2 | 时区感知时间戳(func.now()) / 外键 ondelete 策略 / ProcessingLog 完整定义 / 表名与模型名统一 / ValidationError 导入 / Celery 队列分配规则 / Redis DB 分工 / 统一响应格式+分页Schema+错误码 / JSONB 导入路径 |
| 2026-06-11 | v1.3 | 存储层改用 aiobotocore(S3兼容) / 国产化兼容表(Valkey/人大金仓) / Celery 并发数环境变量 / AI server healthcheck / 锁定版 |
| 2026-06-11 | v1.4 | VMS 任务指数退避重试 / 敏感词库模型(SensitiveWord) / 前端直传(Presigned URL) / TZ=Asia/Shanghai |
| 2026-06-11 | v1.5 | 健康检查(/health+.ready) / API 限流(slowapi) / 全局请求 ID / Celery 全局超时+安全配置 / 数据库连接池调优 / model_version 追溯 / MinIO 桶自动创建 |
| 2026-06-11 | v1.6 | Docker healthcheck+service_healthy / entrypoint alembic upgrade head / 分片上传接口(multipart) / 转码预设表(TranscodePreset) / pgvector 维度明确(Vector(768)) |
| 2026-06-11 | v1.7 | Celery worker 拆分(cpu_io+gpu独立) / API 路径参数统一用 UUID / role_permission+content_tag 多对多关联表 / MediaAsset 完整元数据 / MediaUploadSession 分片上传会话 / Celery Beat 定时任务 / UUID default 写法修正 |
| 2026-06-11 | v1.8 | 模型文件数量修正(13) / SQLAdmin 版本锁定(>=0.27) / Celery result_expires+prefetch / video 队列独立 / pgvector HNSW 参数(m=16,ef_construction=64,ef_search策略) / S3 内部/外部地址拆分 / 权限码规范 / 多站点隔离规则 / 内容生命周期状态机 / AI 服务 API 契约 / Phase 0 验收清单 |
| 2026-06-11 | v1.9 | site_id nullable=False / 种子数据脚本(init_seed.py) / 核心依赖清单(requirements.txt) / 最终锁定版 |
| 2026-06-11 | v2.0 | **[Bug修复]** UUID default 必须用 lambda+str() / 软删除与CASCADE冲突说明+业务层级联 / MinIO CORS配置(前端直传必需) / 内容状态机强制校验(VALID_TRANSITIONS) / 孤儿文件清理(先MinIO后DB) / 转码产物关联(source_media_asset_id) |
| 2026-06-11 | v2.0.1 | Flower 监控服务(docker-compose, :5555) |
