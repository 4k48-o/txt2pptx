# Webhook 生命周期分析

## 问题修复记录

### 问题分析

**问题流程：**
1. 后端在 60 秒无消息时发送 `type: "ping"` 给前端（心跳检测）
2. 前端收到 `type: "ping"` 后，发送 `action: "pong"` 给后端（响应心跳）
3. 后端收到 `action: "pong"` 后，没有处理逻辑，导致报错 "未知的 action: pong"

### 修复内容

在 `app/api/websocket.py` 的 `_handle_client_message` 函数中添加了对 `action: "pong"` 的处理：

```python
elif action == "pong":
    # 前端对 ping 的响应，静默接受即可
    logger.debug(f"收到心跳响应: client_id={client_id}")
```

### 修复后的行为

- **后端发送 `type: "ping"`** → 前端收到后发送 `action: "pong"` → 后端静默接受，不再报错
- **前端发送 `action: "ping"`** → 后端收到后发送 `type: "pong"` → 前端收到后不做任何操作

现在心跳机制应可正常工作，不会再出现 "未知的 action: pong" 错误。

---

## Webhook 生命周期分析

### 阶段 1: 应用启动与 Webhook 注册

**时间**: 14:04:50 - 14:04:51

1. **应用启动**
   - 启动 Manus PPT Generator API
   - 检测到 Webhook 已启用

2. **Webhook 注册**
   - 准备注册: `https://ai.i5hn.com/webhook/manus`
   - `POST /v1/webhooks` → `200 OK`
   - Webhook ID: `dJj9BwdQwSXGHn3q5S8FkS`
   - 注册成功

### 阶段 2: WebSocket 连接建立

**时间**: 14:02:14

1. **客户端连接**
   - WebSocket 连接: `/ws/client_hs4cm64rw_1768456934715`
   - 连接成功，当前连接数: 1

### 阶段 3: 任务创建

**时间**: 14:02:23

1. **创建本地任务**
   - 本地任务 ID: `27fb6f40-78e5-4955-90e2-3e55fee22a0e`
   - Prompt: "大学生喜欢笔记本的品牌分析..."

2. **调用 Manus API 创建任务**
   - `POST /v1/tasks` → `200 OK`
   - Manus 任务 ID: `NXAdNy9BP6nQKd94LCgZEj`
   - 任务标题: "大学生喜欢的笔记本品牌分析"

### 阶段 4: task_created 事件

**时间**: 14:02:25 (任务创建后约 1 秒)

1. **接收 Webhook 回调**
   - Event ID: `task_created_NXAdNy9BP6nQKd94LCgZEj_1768456944`
   - Event Type: `task_created`
   - Task ID: `NXAdNy9BP6nQKd94LCgZEj`
   - Task Title: "大学生喜欢的笔记本品牌分析"
   - Task URL: `https://manus.im/app/NXAdNy9BP6nQKd94LCgZEj`

2. **处理流程**
   - Pydantic 验证成功
   - 记录 Webhook 事件到本地任务
   - 推送事件给 WebSocket 订阅者 (1 个订阅者)
   - 更新本地任务状态为 "processing"
   - 通过 WebSocket 通知前端任务已创建

### 阶段 5: task_progress 事件（多次）

**时间**: 14:02:37 (任务创建后约 12 秒)

1. **接收进度更新**
   - Event ID: `task_progress_NXAdNy9BP6nQKd94LCgZEj_1768456956`
   - Event Type: `task_progress`
   - Progress Type: `plan_update`
   - Message: "收集大学生笔记本电脑品牌偏好数据和市场信息"

2. **处理流程**
   - 记录事件
   - 推送进度更新给订阅者
   - 前端显示实时进度

### 阶段 6: task_stopped 事件（任务完成）

**时间**: 14:04:13 (任务创建后约 1 分 50 秒)

1. **接收任务完成事件**
   - Event ID: `task_stopped_NXAdNy9BP6nQKd94LCgZEj_1768457052`
   - Event Type: `task_stopped`
   - Stop Reason: `finish`
   - Task Title: "大学生喜欢的笔记本品牌分析"
   - Message: "我已经为您生成了这份针对大学生的笔记本电脑品牌分析 PPT..."
   - Attachments: [包含 PPTX 文件信息]

2. **处理流程**
   - 检测到 `stop_reason = "finish"`（任务完成）
   - 开始下载 PPTX 文件
   - 调用 `GET /v1/tasks/{task_id}?convert=true` 获取任务详情
   - 提取 PPTX 下载 URL
   - 下载文件: `output/大学生笔记本品牌分析 2026.pptx` (399518 bytes)
   - 更新本地任务状态为 "completed"
   - 通过 WebSocket 通知前端任务完成
   - 提供下载链接给前端

### 阶段 7: PPTX 下载详情

**时间**: 14:04:13 - 14:04:21

1. **获取任务详情**
   - `GET /v1/tasks/NXAdNy9BP6nQKd94LCgZEj?convert=true` → `200 OK`
   - 提取 PPTX URL (带签名和过期时间)

2. **下载文件**
   - `GET PPTX URL` → `200 OK`
   - 文件大小: 399518 bytes (约 390 KB)
   - 保存路径: `output/大学生笔记本品牌分析 2026.pptx`
   - 下载耗时: 约 8 秒

### 阶段 8: 应用关闭与 Webhook 注销

**时间**: 14:04:49 - 14:04:50

1. **应用关闭流程**
   - 检测到代码变更，触发重载
   - WebSocket 客户端断开连接

2. **Webhook 注销**
   - `DELETE /v1/webhooks/dJj9BwdQwSXGHn3q5S8FkS` → `200 OK`
   - Webhook 删除成功
   - 清理 Manus 客户端连接

---

## 完整生命周期时间线

```
14:02:14  → WebSocket 连接建立
14:02:23  → 创建任务 (本地 + Manus)
14:02:25  → task_created 事件 (1 秒后)
14:02:37  → task_progress 事件 (12 秒后)
14:04:13  → task_stopped 事件 (1分50秒后)
14:04:13  → 开始下载 PPTX
14:04:21  → PPTX 下载完成 (8 秒)
14:04:49  → 应用关闭，Webhook 注销
```

---

## 关键指标

| 指标 | 数值 |
|------|------|
| 任务创建到完成 | 约 1 分 50 秒 |
| Webhook 响应时间 | 立即响应 (200 OK) |
| PPTX 下载时间 | 约 8 秒 |
| WebSocket 推送成功率 | 100% (1/1 订阅者) |
| 事件处理顺序 | `task_created` → `task_progress` → `task_stopped` |

---

## 观察结果

✅ **Webhook 机制正常**：事件及时接收和处理  
✅ **实时推送正常**：WebSocket 成功推送所有事件  
✅ **文件下载正常**：PPTX 文件成功下载  
✅ **生命周期完整**：从创建到完成，所有阶段都有日志记录

**结论**: 系统运行正常，Webhook 生命周期完整。
