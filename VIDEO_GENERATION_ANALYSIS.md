# 视频生成功能代码分析

## 📋 目录
1. [整体架构](#整体架构)
2. [后端代码分析](#后端代码分析)
3. [前端代码分析](#前端代码分析)
4. [数据流程](#数据流程)
5. [关键组件](#关键组件)

---

## 🏗️ 整体架构

视频生成采用**两阶段异步流程**：
1. **脚本生成阶段**：生成 Markdown 格式的视频制作计划
2. **视频生成阶段**：基于脚本生成最终视频文件

### 技术栈
- **后端**：FastAPI + AsyncIO
- **前端**：Vanilla JavaScript + WebSocket
- **通信**：REST API + WebSocket + Webhook
- **外部服务**：Manus AI API

---

## 🔧 后端代码分析

### 1. API 路由层 (`app/api/video/router.py`)

#### 主要端点

**POST `/api/video/tasks`** - 创建视频生成任务
```python
async def create_video_task(request: VideoTaskRequest)
```

**流程**：
1. 验证参数（style、target_audience 是否在支持列表中）
2. 检查 Webhook 是否启用（视频生成必须启用）
3. 创建本地任务记录（保存到 `TaskTrackerService`）
4. 订阅 WebSocket 更新
5. 调用 `VideoGenerationService.generate_video()` 启动脚本生成
6. 返回任务 ID 和状态

**关键代码**：
- 参数验证：检查 `settings.video_supported_styles` 和 `settings.video_supported_audiences`
- 任务元数据：保存 `task_type: "video_generation"`, `step: "script_generation"`
- WebSocket 订阅：同时订阅本地任务 ID 和脚本生成任务 ID

**GET `/api/video/tasks/{task_id}`** - 查询任务状态
- 从 `TaskTrackerService` 获取任务信息
- 返回状态、当前步骤、下载链接等

**GET `/api/video/tasks/{task_id}/download`** - 下载视频
- 验证任务状态（必须已完成）
- 从 metadata 获取 `video_path`
- 返回 `FileResponse`

**GET `/api/video/tasks/{task_id}/markdown`** - 下载 Markdown
- 验证任务状态（脚本生成应已完成）
- 从 metadata 获取 `markdown_path`
- 返回 `FileResponse`

---

### 2. 服务层 (`app/services/video/generation_service.py`)

#### `VideoGenerationService` 类

**核心方法**：

##### `generate_video()` - 主入口
```python
async def generate_video(
    topic: str,
    duration: int,
    style: str,
    target_audience: str,
    local_task_id: str,
) -> Dict[str, Any]
```

**功能**：
- 调用 `VideoScriptService.generate_video_plan()` 创建脚本生成任务
- 更新本地任务元数据（包括 `script_task_id`）
- 返回 `script_task_id`

##### `handle_script_generation_complete()` - 脚本生成完成处理
```python
async def handle_script_generation_complete(
    local_task_id: str,
    script_task_id: str,
) -> Dict[str, Any]
```

**流程**：
1. 获取任务元数据（duration、style）
2. 获取脚本生成任务结果（带重试）
3. 提取 Markdown 文件信息（file_id 或 fileUrl）
4. 构建视频生成 prompt（包含详细的视频规格要求）
5. 创建视频生成任务（将 Markdown 作为附件）
6. 更新任务元数据（`step: "video_generation"`, `video_task_id`）

**关键逻辑**：
- **Markdown 文件处理**：
  - 优先使用 `file_id`（直接从云端使用）
  - 其次使用 `fileUrl`（Manus API 支持直接使用 URL）
  - 最后下载并上传（后备方案）
- **Prompt 构建**：包含详细的视频规格要求（时长、风格、脚本、分镜、背景音乐等）

##### `handle_video_generation_complete()` - 视频生成完成处理
```python
async def handle_video_generation_complete(
    local_task_id: str,
    video_task_id: str,
) -> Dict[str, Any]
```

**流程**：
1. 获取任务元数据（duration）
2. 获取视频生成任务结果（带重试）
3. 下载视频文件（带重试，超时 300 秒）
4. 保存到 `settings.video_storage_dir`
5. 更新任务元数据（`step: "completed"`, `video_path`）

**关键逻辑**：
- **文件下载**：使用 `httpx.AsyncClient` 下载，超时 300 秒
- **文件命名**：`video_{local_task_id[:8]}_{timestamp}.mp4`
- **错误处理**：包含超时、HTTP 错误、IO 错误的处理

---

### 3. Webhook 处理 (`app/api/webhook.py`)

#### `handle_video_task_stopped()` - 视频任务停止事件处理

**流程**：

**当 `task_step == "script_generation"`**：
1. 调用 `video_service.handle_script_generation_complete()`
2. 发送 WebSocket 消息：`script_generation_completed`
3. 发送 WebSocket 消息：`video_generation_started`
4. 订阅视频生成任务

**当 `task_step == "video_generation"`：
1. 调用 `video_service.handle_video_generation_complete()`
2. 更新任务状态为 `completed`
3. 发送 WebSocket 消息：`video_generation_completed`

**错误处理**：
- 捕获异常并发送 `script_generation_failed` 或 `video_generation_failed` 消息
- 更新任务状态为 `failed`

#### `handle_task_progress()` - 任务进度更新

**流程**：
1. 查找本地任务（通过 `manus_task_id`）
2. 根据任务类型和步骤确定进度类型：
   - `script_generation` → `script_generation_progress`
   - `video_generation` → `video_generation_progress`
3. 通过 WebSocket 发送进度消息

---

### 4. 脚本生成服务 (`app/services/video/script_service.py`)

#### `VideoScriptService` 类

**核心方法**：

##### `generate_video_plan()` - 生成视频制作计划
```python
async def generate_video_plan(
    topic: str,
    duration: int,
    style: str,
    target_audience: str,
) -> Dict[str, Any]
```

**流程**：
1. 构建脚本生成 prompt（包含主题、时长、风格、受众等要求）
2. 调用 Manus API 创建任务（带重试）
3. 返回 `task_id`

**Prompt 内容**：
- 要求生成 Markdown 格式的视频制作计划
- 包含：Title、Description、Script、Storyboard、Background Music
- 详细的格式要求和内容规范

---

## 🎨 前端代码分析

### 1. 主要文件 (`static/video/app.js`)

#### 全局变量
```javascript
const APP_BASE = '/manus'  // 基础路径
const API_BASE = '/manus/api'
let currentTaskId = null    // 当前任务 ID
let clientId = null         // WebSocket 客户端 ID
let ws = null               // WebSocket 连接
let wsReconnectTimer = null // 重连定时器
```

#### 核心函数

##### `generateVideo()` - 生成视频
```javascript
window.generateVideo = async function()
```

**流程**：
1. 获取用户输入（topic、duration、style、audience）
2. 验证输入（topic 不能为空）
3. 显示时间轴面板
4. 禁用生成按钮
5. 调用 `POST /api/video/tasks` 创建任务
6. 订阅任务更新（通过 WebSocket）
7. 添加时间轴项显示进度

**API 请求**：
```javascript
POST /api/video/tasks
{
    topic: "Introduction to AI",
    duration: 15,
    style: "educational",
    target_audience: "general",
    client_id: "client_xxx"
}
```

##### `initWebSocket()` - 初始化 WebSocket
```javascript
function initWebSocket()
```

**流程**：
1. 生成 `clientId`（格式：`client_{timestamp}_{random}`）
2. 连接 WebSocket：`ws://host/manus/ws/{clientId}`
3. 设置事件处理器：
   - `onopen`：发送订阅消息（如果有当前任务）
   - `onmessage`：调用 `handleWebSocketMessage()`
   - `onerror`：更新状态显示
   - `onclose`：3 秒后自动重连

##### `handleWebSocketMessage()` - 处理 WebSocket 消息
```javascript
function handleWebSocketMessage(data)
```

**消息类型处理**：

| 消息类型 | 处理逻辑 |
|---------|---------|
| `connected` | 更新 WebSocket 状态为已连接 |
| `script_generation_progress` | 添加进度时间轴项 |
| `video_generation_progress` | 添加进度时间轴项 |
| `script_generation_completed` | 添加完成项，订阅视频生成任务 |
| `video_generation_started` | 添加进度项 |
| `video_generation_completed` | 更新所有项为完成，显示下载按钮 |
| `script_generation_failed` | 更新所有项为错误，恢复按钮 |
| `video_generation_failed` | 更新所有项为错误，恢复按钮 |

##### `addTimelineItem()` - 添加时间轴项
```javascript
function addTimelineItem(type, title, message, timestamp)
```

**功能**：
- 创建时间轴项 DOM 元素
- 根据类型（progress/completed/error）应用不同样式
- progress 类型添加 `active` 类（显示光影动画效果）
- 自动滚动到底部

##### `downloadVideo()` - 下载视频
```javascript
window.downloadVideo = function()
```

**功能**：
- 打开新窗口下载视频：`/api/video/tasks/{currentTaskId}/download`

---

## 🔄 数据流程

### 完整流程图

```
用户操作
  ↓
前端：generateVideo()
  ↓
POST /api/video/tasks
  ↓
后端：create_video_task()
  ├─ 创建本地任务记录
  ├─ 订阅 WebSocket
  └─ 调用 VideoGenerationService.generate_video()
      ↓
      VideoScriptService.generate_video_plan()
      ↓
      调用 Manus API 创建脚本生成任务
      ↓
      返回 script_task_id
  ↓
返回 task_id 给前端
  ↓
前端：订阅任务更新（WebSocket）
  ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
脚本生成阶段（异步）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓
Manus API 处理脚本生成
  ↓
Manus API 发送 Webhook：task_progress
  ↓
后端：handle_task_progress()
  ↓
通过 WebSocket 发送：script_generation_progress
  ↓
前端：显示进度更新
  ↓
Manus API 发送 Webhook：task_stopped (finish)
  ↓
后端：handle_video_task_stopped()
  ├─ 判断 task_step == "script_generation"
  ├─ 调用 handle_script_generation_complete()
  │   ├─ 获取脚本生成结果
  │   ├─ 提取 Markdown 文件（file_id/fileUrl）
  │   ├─ 构建视频生成 prompt
  │   └─ 创建视频生成任务（Markdown 作为附件）
  ├─ 发送 WebSocket：script_generation_completed
  └─ 发送 WebSocket：video_generation_started
  ↓
前端：显示脚本生成完成，开始视频生成
  ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
视频生成阶段（异步）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓
Manus API 处理视频生成
  ↓
Manus API 发送 Webhook：task_progress
  ↓
后端：handle_task_progress()
  ↓
通过 WebSocket 发送：video_generation_progress
  ↓
前端：显示进度更新
  ↓
Manus API 发送 Webhook：task_stopped (finish)
  ↓
后端：handle_video_task_stopped()
  ├─ 判断 task_step == "video_generation"
  ├─ 调用 handle_video_generation_complete()
  │   ├─ 获取视频生成结果
  │   ├─ 下载视频文件
  │   └─ 保存到本地存储
  ├─ 更新任务状态为 completed
  └─ 发送 WebSocket：video_generation_completed
  ↓
前端：显示完成，显示下载按钮
  ↓
用户点击下载
  ↓
GET /api/video/tasks/{task_id}/download
  ↓
返回视频文件
```

---

## 🔑 关键组件

### 1. 任务追踪 (`TaskTrackerService`)

**作用**：
- 管理本地任务记录（JSON 文件存储）
- 关联本地任务 ID 和 Manus 任务 ID
- 保存任务元数据（task_type、step、参数等）

**关键字段**：
- `id`：本地任务 ID（UUID）
- `manus_task_id`：Manus 任务 ID（用于 Webhook 查找）
- `metadata`：任务元数据
  - `task_type: "video_generation"`
  - `step: "script_generation" | "video_generation" | "completed"`
  - `script_task_id`、`video_task_id`
  - `topic`、`duration`、`style`、`target_audience`
  - `video_path`、`markdown_path`

### 2. WebSocket 管理器 (`app/websocket/manager.py`)

**作用**：
- 管理 WebSocket 连接
- 任务订阅管理
- 消息广播

**关键方法**：
- `subscribe_task(client_id, task_id)`：订阅任务更新
- `send_to_task_subscribers(task_id, message)`：发送消息给所有订阅者

### 3. 重试机制 (`app/utils/retry.py`)

**作用**：
- 提供异步重试功能
- 支持指数退避

**使用场景**：
- 获取任务结果（最多 3 次，初始延迟 1 秒）
- 创建任务（最多 3 次，初始延迟 1 秒）
- 下载文件（最多 3 次，初始延迟 2 秒，超时 60 秒）

---

## 📊 数据模型

### VideoTaskRequest
```python
{
    "topic": str,              # 视频主题
    "duration": int,           # 时长（5-30 秒）
    "style": str,              # 风格（educational/promotional/...）
    "target_audience": str,    # 受众（general/students/...）
    "client_id": str (可选)    # WebSocket 客户端 ID
}
```

### VideoTaskResponse
```python
{
    "task_id": str,            # 本地任务 ID
    "status": str,             # pending/processing/completed/failed
    "step": str,               # script_generation/video_generation
    "video_url": str (可选),   # 视频下载链接
    "markdown_url": str (可选), # Markdown 下载链接
    "message": str (可选)      # 状态消息
}
```

### WebSocket 消息格式

**进度更新**：
```json
{
    "type": "script_generation_progress" | "video_generation_progress",
    "task_id": "xxx",
    "message": "Processing...",
    "timestamp": "2026-01-21T11:00:00"
}
```

**脚本生成完成**：
```json
{
    "type": "script_generation_completed",
    "task_id": "script_task_id",
    "local_task_id": "local_task_id",
    "video_task_id": "video_task_id",
    "message": "脚本生成完成，开始生成视频",
    "timestamp": "2026-01-21T11:00:00"
}
```

**视频生成完成**：
```json
{
    "type": "video_generation_completed",
    "task_id": "video_task_id",
    "local_task_id": "local_task_id",
    "video_path": "/path/to/video.mp4",
    "download_url": "/api/video/tasks/{local_task_id}/download",
    "message": "视频生成完成！",
    "timestamp": "2026-01-21T11:00:00"
}
```

---

## 🎯 关键特性

### 1. 异步处理
- 所有 Manus API 调用都是异步的
- 使用 Webhook 接收任务完成通知
- 使用 WebSocket 实时推送进度

### 2. 错误处理
- 重试机制（API 调用、文件下载）
- 异常捕获和日志记录
- 任务状态更新为 `failed`
- WebSocket 错误消息推送

### 3. 状态管理
- 本地任务状态：`pending` → `processing` → `completed`/`failed`
- 任务步骤：`script_generation` → `video_generation` → `completed`
- 通过 metadata 保存中间状态和参数

### 4. 文件管理
- Markdown 文件：优先使用云端 file_id，其次 fileUrl，最后下载上传
- 视频文件：下载到本地存储目录
- 文件路径保存在任务 metadata 中

### 5. 实时更新
- WebSocket 连接管理（自动重连）
- 任务订阅机制
- 进度消息实时推送
- 前端时间轴可视化

---

## 🔍 代码质量分析

### 优点
1. ✅ **清晰的职责分离**：API 路由、服务层、Webhook 处理分离
2. ✅ **完善的错误处理**：重试机制、异常捕获、状态更新
3. ✅ **实时通信**：WebSocket + Webhook 双重保障
4. ✅ **详细的日志记录**：便于调试和监控
5. ✅ **类型安全**：使用 Pydantic 模型验证

### 可改进点
1. ⚠️ **视频时长验证**：`_get_video_duration()` 未实现（TODO）
2. ⚠️ **文件清理**：没有自动清理旧文件的机制
3. ⚠️ **并发控制**：没有限制同时进行的任务数量
4. ⚠️ **进度估算**：前端无法显示预计完成时间
5. ⚠️ **断点续传**：文件下载不支持断点续传

---

## 📝 总结

视频生成功能采用**两阶段异步流程**，通过 **Webhook + WebSocket** 实现实时状态更新。后端代码结构清晰，错误处理完善，前端交互流畅。整体架构合理，代码质量较高。

**核心优势**：
- 异步处理，不阻塞用户
- 实时进度更新
- 完善的错误处理
- 清晰的代码结构

**建议优化**：
- 实现视频时长验证
- 添加文件清理机制
- 增加并发控制
- 优化进度显示
