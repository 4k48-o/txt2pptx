# 任务明细查询接口文档

## 概述

工程中提供了多个查看任务明细的接口，支持不同类型的任务（PPT、视频、爬虫等）。

## 通用任务接口

### 1. 获取任务详情（本地信息）

**端点**：`GET /api/tasks/{task_id}/detail`

**描述**：获取任务的本地存储信息，包括基本信息和下载链接

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": "task_id",
    "manus_task_id": "manus_task_id",
    "status": "completed",
    "prompt": "任务提示词",
    "title": "任务标题",
    "task_url": "https://manus.im/app/xxx",
    "pptx_url": "https://...",
    "pptx_filename": "文件名.pptx",
    "local_file_path": "output/xxx.pptx",
    "credit_usage": 21,
    "error": null,
    "created_at": "2026-01-21T03:14:11.663529",
    "updated_at": "2026-01-21T03:17:36.655795",
    "completed_at": "2026-01-21T03:17:36.655806"
  }
}
```

### 2. 获取任务完整详情（含 Manus API 数据）

**端点**：`GET /api/tasks/{task_id}/full`

**描述**：从 Manus API 获取任务的完整信息，包括所有生成的文件和输出消息

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": "task_id",
    "status": "completed",
    "prompt": "任务提示词",
    "title": "任务标题",
    "task_url": "https://manus.im/app/xxx",
    "credit_usage": 21,
    "created_at": "2026-01-21T03:14:11",
    "updated_at": "2026-01-21T03:17:36",
    "files": [
      {
        "fileUrl": "https://...",
        "fileName": "xxx.pptx",
        "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
      }
    ],
    "output": [...],  // 完整的输出消息数组
    "local_file_path": "output/xxx.pptx"
  }
}
```

### 3. 通过 Manus 任务 ID 查询

**端点**：`GET /api/tasks/manus/{manus_task_id}`

**描述**：直接通过 Manus 任务 ID 从 Manus API 查询任务详情（无需本地任务记录）

**响应**：返回 Manus API 的原始任务数据

## PPT 任务接口

### 1. 获取 PPT 任务详情

**端点**：`GET /api/ppt/{task_id}`

**描述**：获取 PPT 任务的基本信息

### 2. 获取 PPT 任务完整详情

**端点**：`GET /api/ppt/{task_id}/detail`

**描述**：获取 PPT 任务的所有本地信息

### 3. 获取 PPT 任务完整详情（含文件）

**端点**：`GET /api/ppt/{task_id}/full`

**描述**：从 Manus API 获取 PPT 任务的完整信息，包括所有生成的文件

### 4. 通过 Manus 任务 ID 查询 PPT 任务

**端点**：`GET /api/ppt/manus/{manus_task_id}`

**描述**：直接通过 Manus 任务 ID 查询 PPT 任务详情

## 视频任务接口

### 1. 获取视频任务详情

**端点**：`GET /api/video/tasks/{task_id}`

**描述**：查询视频生成任务的详细信息，包括状态、当前步骤、下载链接等

**响应示例**：
```json
{
  "success": true,
  "data": {
    "task_id": "task_id",
    "status": "processing",
    "step": "video_generation",
    "video_url": "/api/video/tasks/{task_id}/download",
    "markdown_url": "/api/video/tasks/{task_id}/markdown",
    "message": "任务状态: processing, 当前步骤: video_generation"
  },
  "message": "查询成功"
}
```

## Webhook 事件接口

### 获取任务的 Webhook 事件

**端点**：`GET /api/webhook/events/{task_id}`

**描述**：获取任务的所有 webhook 事件历史

**响应**：返回任务的 webhook_events 数组

## 使用建议

### 查看本地任务信息
使用 `/api/tasks/{task_id}/detail` 或 `/api/ppt/{task_id}/detail`

### 查看完整任务信息（含 Manus API 数据）
使用 `/api/tasks/{task_id}/full` 或 `/api/ppt/{task_id}/full`

### 查看视频任务信息
使用 `/api/video/tasks/{task_id}`

### 查看任务历史事件
使用 `/api/webhook/events/{task_id}`

## 注意事项

1. **任务 ID**：所有接口使用的都是**本地任务 ID**（不是 Manus 任务 ID）
2. **Manus 任务 ID**：如果需要通过 Manus 任务 ID 查询，使用 `/api/tasks/manus/{manus_task_id}` 或 `/api/ppt/manus/{manus_task_id}`
3. **完整详情**：`/full` 接口会调用 Manus API，可能需要更长时间
4. **错误处理**：如果 Manus API 调用失败，`/full` 接口会返回本地信息
