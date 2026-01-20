# Webhooks

> 用于任务生命周期事件的实时通知

## 概览

Webhooks 允许你在 Manus 任务发生关键事件时，收到实时通知。注册 webhook 之后，当这些事件触发时，Manus 会向你配置的回调 URL 发送 HTTP POST 请求。

## Webhook 事件是如何工作的

当你创建并执行任务时，三个关键的生命周期事件会触发 webhook 推送：

* **任务创建**（`task_created`）：当一个任务通过 API 首次创建时发送，**只会发送一次**
* **任务进度**（`task_progress`）：任务执行过程中会多次发送，用于推送计划更新/进度变化
* **任务停止**（`task_stopped`）：任务完成或需要用户输入时发送

### 典型事件生命周期

针对一个任务，你通常会按如下顺序收到 webhooks：

1. 任务创建时收到 **一次** `task_created`
2. 任务执行与计划更新过程中收到 **多次** `task_progress`（可选，次数可能因任务而异）
3. 任务结束或需要输入时收到 **一次** `task_stopped`

每次 webhook 推送都会包含一个明确的事件类型标识（`event_type`）以及结构化 payload（包含相关任务信息）。你的服务端可以像处理普通 API 请求一样处理这些标准 HTTP POST 请求。

## 配置 Webhooks

<Card title="管理 Webhooks" horizontal arrow icon="wrench" href="http://manus.im/app?show_settings=integrations&app_name=api">
  打开 API Integration（API 集成）设置页面，创建或管理 webhooks。
</Card>

在启用 webhook 之前，Manus 会先发送一条测试请求，用于验证你的回调端点可访问且响应正确。你的端点需要满足：

* 返回 HTTP 200 状态码
* 接受携带 JSON payload 的 POST 请求
* 在 10 秒内完成响应

## 安全注意事项

<Warning>
  请在你的应用中对 webhook payload 做校验。建议实现签名校验或其他安全措施，以确保请求确实来自 Manus。
</Warning>

## 事件类型与 Payload

### `task_created` 事件

**触发时机：** 新任务创建成功后立即触发。

**用途：** 便于你在自己的系统中跟踪任务创建（例如发送确认邮件、实时更新看板等）。

**Payload Schema：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_id` | string | Yes | 本次 webhook 事件的唯一标识 |
| `event_type` | string | Yes | 对该事件恒为 `"task_created"` |
| `task_id` | string | Yes | 被创建任务的唯一 ID |
| `task_title` | string | Yes | 任务的人类可读标题 |
| `task_url` | string | Yes | 在 Manus app 中查看任务的直达 URL |

**示例 Payload：**

```json  theme={null}
{
  "event_id": "task_created_task_abc123",
  "event_type": "task_created",
  "task_detail":{
    "task_id": "task_abc123",
    "task_title": "Generate quarterly sales report",
    "task_url": "https://manus.im/app/task_abc123",
  }
}
```

### `task_progress` 事件

**触发时机：** 任务执行过程中，随着计划更新或进度推进会多次触发。

**用途：** 支持实时进度跟踪，让你可以向用户展示实时更新，或对任务执行细节进行监控。

**Payload Schema：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_id` | string | Yes | 本次 webhook 事件的唯一标识 |
| `event_type` | string | Yes | 对该事件恒为 `"task_progress"` |
| `task_id` | string | Yes | 任务唯一 ID |
| `progress_type` | string | Yes | 进度更新类型（例如 `"plan_update"`） |
| `message` | string | Yes | 当前进度描述或计划步骤描述 |

**Progress Type 取值：**

* `"plan_update"`：任务更新了执行计划，产生了新的步骤

**示例 Payload：**

```json  theme={null}
{
  "event_id": "task_progress_TeBim6FDQf9peS52xHtAyh_1764187289",
  "event_type": "task_progress",
  "progress_detail": {
    "task_id": "TeBim6FDQf9peS52xHtAyh",
    "progress_type": "plan_update",
    "message": "Generate the TypeScript \"hello world\" function code."
  }
}
```

### `task_stopped` 事件

**触发时机：** 任务到达“停止点”时触发——要么任务已成功完成，要么需要用户输入才能继续。

**用途：** 用于判断任务何时结束以及最终结果是什么，可据此触发自动化工作流。

**Payload Schema：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_id` | string | Yes | 本次 webhook 事件的唯一标识 |
| `event_type` | string | Yes | 对该事件恒为 `"task_stopped"` |
| `task_id` | string | Yes | 任务唯一 ID |
| `task_title` | string | Yes | 任务的人类可读标题 |
| `task_url` | string | Yes | 在 Manus app 中查看任务的直达 URL |
| `message` | string | Yes | 任务执行返回的状态信息 |
| `attachments` | array | No | 任务生成的文件列表 |
| `stop_reason` | string | Yes | 任务停止原因：`"finish"` 或 `"ask"` |

**Stop Reason 取值：**

* `"finish"`：任务成功完成，并产生最终结果
* `"ask"`：任务暂停，需用户输入或确认后才能继续

**Attachment 对象 Schema：**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file_name` | string | Yes | 生成文件名 |
| `url` | string | Yes | 文件安全下载 URL |
| `size_bytes` | integer | Yes | 文件大小（字节） |

**示例 Payload（任务完成）：**

```json  theme={null}
{
  "event_id": "task_created_task_abc123",
  "event_type": "task_stopped",
  "task_detail": {
    "task_id": "task_abc123",
    "task_title": "Generate quarterly sales report",
    "task_url": "https://manus.im/app/task_abc123",
    "message": "I've completed the quarterly sales report analysis. The report includes revenue trends, top-performing products, and regional breakdowns.",
    "attachments": [
      {
        "file_name": "q4-sales-report.pdf",
        "url": "https://s3.amazonaws.com/manus-files/reports/q4-sales-report.pdf",
        "size_bytes": 2048576
      },
      {
        "file_name": "sales-data.xlsx",
        "url": "https://s3.amazonaws.com/manus-files/reports/sales-data.xlsx",
        "size_bytes": 512000
      }
    ],
    "stop_reason": "finish"
  }
}
```

**示例 Payload（需要用户输入）：**

```json  theme={null}
{
  "event_id": "task_created_task_abc123",
  "event_type": "task_stopped",
  "task_detail": {
    "task_id": "task_abc123",
    "task_title": "Book restaurant reservation",
    "task_url": "https://manus.im/app/task_abc123",
    "message": "I found several restaurants with availability for your requested date and time. Which option would you prefer? 1) Bistro Milano - 7:00 PM, 2) Garden Terrace - 7:30 PM, 3) The Blue Door - 8:00 PM",
    "attachments": [],
    "stop_reason": "ask"
  }
}
```

## 端到端 Webhook 生命周期示例

下面演示了一个任务完整的 webhook 序列可能长什么样：

```json  theme={null}
// 1. Task Created（只发送一次）
{
  "event_id": "task_created_TeBim6FDQf9peS52xHtAyh_1764187286",
  "event_type": "task_created",
  "task_detail": {
    "task_id": "TeBim6FDQf9peS52xHtAyh",
    "task_title": "Hello World Function in TypeScript",
    "task_url": "https://manus.im/app/TeBim6FDQf9peS52xHtAyh"
  }
}

// 2. Progress Update #1（任务执行过程中推送）
{
  "event_id": "task_progress_TeBim6FDQf9peS52xHtAyh_1764187289",
  "event_type": "task_progress",
  "progress_detail": {
    "task_id": "TeBim6FDQf9peS52xHtAyh",
    "progress_type": "plan_update",
    "message": "Generate the TypeScript \"hello world\" function code."
  }
}

// 3. Progress Update #2（任务继续执行时推送）
{
  "event_id": "task_progress_TeBim6FDQf9peS52xHtAyh_1764187298",
  "event_type": "task_progress",
  "progress_detail": {
    "task_id": "TeBim6FDQf9peS52xHtAyh",
    "progress_type": "plan_update",
    "message": "Deliver the TypeScript code to the user."
  }
}

// 4. Task Stopped（任务完成时只发送一次）
{
  "event_id": "task_stopped_TeBim6FDQf9peS52xHtAyh_1764187304",
  "event_type": "task_stopped",
  "task_detail": {
    "task_id": "TeBim6FDQf9peS52xHtAyh",
    "task_title": "Hello World Function in TypeScript",
    "task_url": "https://manus.im/app/TeBim6FDQf9peS52xHtAyh",
    "message": "Here is the simple \"hello world\" function written in TypeScript...",
    "attachments": [
      {
        "file_name": "hello_world.ts",
        "url": "https://manus.im/files/hello_world.ts",
        "size_bytes": 108
      }
    ],
    "stop_reason": "finish"
  }
}
```

**端到端使用 Webhooks：**

1. **任务创建**：收到 `task_created` 后，你可以把 task ID 存到数据库，并向用户展示“任务已开始”。
2. **进度更新**：收到 `task_progress` 后，更新进度条或活动日志，让用户实时看到 AI 在做什么。
3. **任务完成**：当收到 `task_stopped` 且 `stop_reason: "finish"` 时，你可以：
   * 下载 payload 里提供的附件 URL
   * 保存最终 message 与结果
   * 发送完成通知
   * 触发下游自动化流程
4. **需要输入**：当收到 `task_stopped` 且 `stop_reason: "ask"` 时，把 message 展示给用户并收集其回复，以继续任务。

## 集成示例

### 通过 Zapier 发送邮件通知

把你的 webhook 接到 Zapier，可以在任务完成时自动发送邮件通知：

1. 创建一个 Zapier webhook 触发器
2. 在 Manus webhook 配置中填入该 webhook URL
3. 基于 `stop_reason` 字段设置后续邮件动作

### Slack 集成

把任务更新直接推送到 Slack channel：

```javascript  theme={null}
// Example webhook handler for Slack integration
app.post('/manus-webhook', (req, res) => {
  const { task_title, message, stop_reason } = req.body;

  if (stop_reason === 'finish') {
    // Post completion message to Slack
    slack.chat.postMessage({
      channel: '#ai-tasks',
      text: `✅ Task completed: ${task_title}\n${message}`
    });
  }

  res.status(200).send('OK');
});
```

### 自定义看板更新

实时更新你内部的仪表盘：

```python  theme={null}
# Example webhook handler in Python/Flask
@app.route('/manus-webhook', methods=['POST'])
def handle_webhook():
    data = request.json

    # Update task status in your database
    update_task_status(
        task_id=data['task_id'],
        status='completed' if data['stop_reason'] == 'finish' else 'waiting',
        message=data['message']
    )

    return '', 200
```

## 故障排查

### 常见问题

* **Webhook 收不到事件**：确认 URL 可访问，且返回 200
* **SSL/TLS 错误**：确保你的端点使用有效的 HTTPS 证书
* **超时**：确保端点在 10 秒内返回响应

### 测试你的 Webhook

你可以使用这些工具测试 webhook 端点：

* 使用 [webhook.site](https://webhook.site) 快速测试
* 使用 [ngrok](https://ngrok.com) 进行本地开发联调
* 使用 Postman 或 curl 手工测试


---

> 若要查看本套文档的导航与其他页面，请访问 llms.txt：`https://open.manus.ai/docs/llms.txt`

