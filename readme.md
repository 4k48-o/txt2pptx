下面是一个为 **使用  Manus API 的 “自动生成 PPT” 应用** 的开发计划任务（Task Plan）。

---

# 📌 项目名称（可修改）

**自动化 PPT 生成器（Manus API 集成）**

---

## 🎯 项目目标

开发一个前后端或 CLI/服务层应用，用户输入主题/内容（文字、PDF、数据等）后，自动调用 Manus API 生成结构化的 PowerPoint (.pptx) 文件，并返回给用户下载或进一步编辑。

---

## 🧱 核心功能板块

1. **输入收集模块**

   * 用户输入：文本主题、详细提示（Prompt）、上传文件（如 PDF/Word/数据文件）；
   * 输入验证、格式标准化。
2. **Manus 任务创建模块**

   * 构建 Manus API 请求，传入提示、上下文文件、模板参数；
   * 管理任务关联（项目/任务/文件）；
   * 监听任务状态（轮询或 webhook）。
3. **文件管理模块**

   * Manus 文件上传/管理接口；
   * 自动关联文件至任务输入；
   * 支持各种附件格式（PDF/Word/图表/研究数据）。
4. **结果处理与导出模块**

   * 获取生成结果；
   * 下载 .pptx 文件；
   * 支持导出为 PDF。
5. **模板/样式管理模块**

   * 可选择 PPT 模板；
   * 支持自定义样式／预设；
   * 可利用用户上传的模板应用至生成输出。
6. **错误处理/日志模块**

   * 任务失败重试机制；
   * 生成日志记录与调试工具；
   * Prompt 调整建议与优化策略。
7. **界面层 (可选)**

   * 简易 Web UI / 界面；
   * 状态反馈（进度／运行中／完成）；
   * 下载按钮／自动推送回调。

---

## 🧠 技术栈

### 一期技术栈

| 层 | 技术/方案 | 说明 |
| --- | --- | --- |
| 核心语言 | Python 3.10+ | |
| HTTP 客户端 | Requests | API 调用 |
| 存储 | 本地文件系统 | 存储下载的 PPT |
| 配置管理 | python-dotenv | 环境变量管理 |
| 日志 | logging | 标准库 |

### 二期技术栈（规划）

| 层 | 技术/方案 | 说明 |
| --- | --- | --- |
| Web 框架 | FastAPI | REST API 服务 |
| 异步队列 | Celery + Redis | 后台任务处理 |
| 前端 | Vue/React | Web UI |

---

## 🔗 Manus API 详细信息

> 基于 [Manus API 官方文档](https://open.manus.ai/docs) 整理

### API 基础信息

| 项目 | 值 |
|------|-----|
| **Base URL** | `https://api.manus.ai` |
| **认证方式** | Header: `API_KEY: $MANUS_API_KEY` |
| **API 版本** | v1 (OpenAPI 3.1.0) |

### 核心 API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/tasks` | 创建新任务 |
| GET | `/v1/tasks/{task_id}` | 获取任务详情（支持 `convert=true` 参数转换 pptx） |
| GET | `/v1/tasks` | 获取任务列表（支持分页和过滤） |
| DELETE | `/v1/tasks/{task_id}` | 删除任务 |
| POST | `/v1/files` | 创建文件记录，返回 presigned URL |
| GET | `/v1/files` | 获取最近上传的 10 个文件 |
| DELETE | `/v1/files/{file_id}` | 删除文件 |
| POST | `/v1/webhooks` | 创建 Webhook |
| DELETE | `/v1/webhooks/{webhook_id}` | 删除 Webhook |
| POST | `/v1/projects` | 创建项目 |
| GET | `/v1/projects` | 获取项目列表 |

### 文件上传流程（两步）

1. **创建文件记录**：`POST /v1/files` 传入 `filename`，返回 `file_id` 和 `presigned_url`
2. **上传文件内容**：使用返回的 `presigned_url` PUT 上传实际文件到 S3
3. **在任务中引用**：创建任务时通过 `attachments` 数组传入 `file_id`

```python
# 示例：创建任务时附加文件
{
    "prompt": "生成一份关于AI的PPT",
    "attachments": [
        {
            "filename": "reference.pdf",
            "file_id": "之前上传获得的 file_id"
        }
    ]
}
```

### Webhook 事件

| 事件类型 | 触发时机 |
|----------|----------|
| `task_created` | 任务创建成功后立即触发 |
| `task_state_change` | 任务完成或需要用户输入时触发 |

**Webhook 要求**：
- 响应 HTTP 200 状态码
- 接受 POST 请求，Content-Type: application/json
- 10 秒内响应

**Webhook Payload 示例**：
```json
{
    "event_id": "task_created_task_abc123",
    "event_type": "task_created",
    "task_id": "xxx",
    "task_title": "生成 AI PPT",
    "task_url": "https://manus.im/task/xxx"
}
```

### 文件上传限制

- **文件大小上限**：10 MB
- **支持格式**：PDF、Word、文本等常见文档格式

### PPT 模板/样式

- 通过 **prompt 描述**来指定 PPT 风格和模板
- 在 prompt 中描述所需的风格、配色、布局等

### 任务状态枚举值

| 状态 | 说明 |
|------|------|
| `pending` | 待处理 |
| `running` | 运行中 |
| `completed` | 已完成 |
| `failed` | 失败 |

---

## 📅 开发里程碑与任务拆解

> 分期开发，一期聚焦后端核心功能

---

## 🚀 一期：Python 后端核心（当前阶段）

> 目标：构建完整的 Manus API 封装，实现 PPT 生成核心流程

### ✨ Milestone 1 — 项目初始化

**Task 1 — 建立 Repo 与基础结构**

* 初始化项目、安装依赖、配置环境变量；
* 包含 `MANUS_API_KEY` 配置。

**Task 2 — 项目结构设计**

* 设计模块化的项目结构；
* 配置日志、异常处理等基础设施。

---

### 🛠 Milestone 2 — Manus API 核心功能实现

**Task 3 — REST 客户端封装 Module**

* 实现 Manus API 访问基础类；
* 统一的请求/响应处理、错误处理。

**Task 4 — 上传文件支持**

* 实现两步上传流程（获取 presigned URL → 上传到 S3）；
* 支持 PDF/Word/文本格式，限制 10MB；
* 返回 `file_id` 供创建任务使用。

**Task 5 — 创建 Manus PPT 任务**

* 构建生成 PPT 的 Prompt；
* 支持附加文件作为上下文；
* 调用 Manus 任务创建 API 并返回 Task ID。

---

### 🔄 Milestone 3 — 任务状态轮询

**Task 6 — 实现轮询任务状态**

* 每隔 N 秒检查任务状态（pending → running → completed/failed）；
* 支持超时控制和重试机制；
* 输出进度信息到日志/控制台。

---

### 📦 Milestone 4 — 结果处理和导出

**Task 7 — 获取任务结果 / 下载文件**

* 任务完成后获取生成的 PPT 下载链接；
* 自动下载 .pptx 文件到本地存储。

---

### 🧪 Milestone 5 — 测试与验证

**Task 8 — 集成测试**

* 端到端测试：上传文件 → 创建任务 → 轮询状态 → 下载结果；
* 测试错误处理：API 失败、网络错误、文件过大等。

---

## 📋 二期规划（暂不实现）

> 以下功能在一期完成后根据需求开发

### 🎨 模板/样式管理
- 预设多个 PPT 风格 Prompt 模板
- 用户自定义模板管理

### 📊 Web UI
- 构建 FastAPI Web 服务
- 前端界面：输入表单、进度展示、下载按钮

### 🔔 Webhook 回调（可选）
- 创建 Webhook 接收 Manus 回调
- 替代轮询，提高效率

### 📄 多格式导出
- PDF 导出支持
- 其他格式转换

### 🔧 高级功能
- Celery 异步任务队列
- 批量任务处理
- Prompt 优化与 A/B 测试

---

## 🔑 示例 Prompt 结构（给 Manus 任务）

```text
生成一份 PPT，主题为 "{{topic}}"
目标受众：{{audience}}
要求：
- 页数：约 {{slides_count}}
- 每页包含 标题、要点、图表（如适用）
- 如果已有 PDF/Word 作为输入，请整合其关键内容
- 使用 {{template}} 模板
- 导出格式：PPTX
```

*(用于创建 Manus 任务的 prompt)*

---

## 📌 注意事项

✅ Manus 支持自动生成 PPT，并能输出为 PowerPoint (.pptx) 格式。([Manus][1])
✅ 生成所需积分 / 运行时间取决于内容复杂度。([53AI][2])
✅ 任务中可能需要上传文件并在创建任务时引用；处理文件上传逻辑是关键一环。([Manus][3])

---

如果你需要，我还可以补充：

📌 **具体代码示例**（如 Node.js/Python 版 Manus API 调用 + PPT 模块）
📌 **自动 Prompt 优化策略与反馈循环设计**

随时问我！

[1]: https://manus.im/docs/zh-cn/features/slides?utm_source=chatgpt.com "Manus 幻灯片 - Manus Documentation"
[2]: https://www.53ai.com/news/LargeLanguageModel/2025060423167.html?utm_source=chatgpt.com "Manus新功能一手实测！10分钟8页PPT，网友：当前第一名没跑 - 53AI-AI知识库|企业AI知识库|大模型知识库|AIHub"
[3]: https://manus.im/docs/ja/integrations/manus-api?utm_source=chatgpt.com "Manus API - Manus Documentation"
