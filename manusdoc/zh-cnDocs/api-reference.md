# 概览

Manus API 提供了一组 RESTful 端点，用于以编程方式管理 projects、tasks、files 以及 webhooks。

**Base URL**：`https://api.manus.ai`

**认证方式**：每次请求都需要在请求头 `API_KEY` 中携带你的 API key。

```bash  theme={null}
curl -H "API_KEY: your-api-key" https://api.manus.ai/v1/tasks
```

## 资源

| 实体 | 端点 | 说明 |
| --- | --- | --- |
| **Projects** | Create Project | 创建一个新 project（带默认 instructions） |
|  | List Projects | 获取 projects 列表 |
| **Tasks** | Create Task | 通过 prompt 与附件提交一个新任务 |
|  | Get Tasks | 按条件过滤与分页列出 tasks |
|  | Get Task | 按 ID 获取某个 task |
|  | Update Task | 修改已有 task |
|  | Delete Task | 删除 task |
| **Files** | Create File | 获取上传文件的 presigned URL |
|  | List Files | 获取已上传文件列表 |
|  | Get File | 获取某个 file 的详情 |
|  | Delete File | 删除 file |
| **Webhooks** | Create Webhook | 注册一个新的 webhook URL |
|  | Delete Webhook | 删除一个 webhook 订阅 |


---

> 若要查看本套文档的导航与其他页面，请访问 llms.txt：`https://open.manus.ai/docs/llms.txt`

