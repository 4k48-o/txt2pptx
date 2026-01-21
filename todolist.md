# 三服务架构重构 TODO List

## 项目目标
将现有项目重构为三个独立服务：
1. **PPT 生成服务** (`/manus/ppt`)
2. **视频生成服务** (`/manus/video`)
3. **爬虫服务** (`/manus/crawler`)

每个服务前后端完全隔离，URL 结构统一为：`https://ai.i5hn.com/manus/{service_name}`

---

## 📋 一、后端路由重构

### 1.1 创建服务路由模块结构
- [x] 创建 `app/api/ppt/` 目录
  - [x] `__init__.py` - PPT 服务路由模块初始化
  - [x] `router.py` - PPT 服务主路由（整合现有的 tasks.py 和 tasks_v2.py）
  - [x] `files.py` - PPT 服务文件管理路由（从现有 files.py 迁移）
  
- [x] 创建 `app/api/video/` 目录
  - [x] `__init__.py` - 视频服务路由模块初始化
  - [x] `router.py` - 视频服务主路由（重构现有的 video.py）
  
- [x] 创建 `app/api/crawler/` 目录
  - [x] `__init__.py` - 爬虫服务路由模块初始化
  - [x] `router.py` - 爬虫服务主路由（新建）
  - [ ] `scheduler.py` - 爬虫任务调度路由（可选，待实现）

### 1.2 重构主路由配置
- [x] 修改 `app/api/router.py`
  - [x] 移除直接导入 tasks、video 等路由
  - [x] 导入三个服务的路由模块
  - [x] 注册服务路由：
    - [x] `/api/ppt/*` - PPT 服务 API
    - [x] `/api/video/*` - 视频服务 API
    - [x] `/api/crawler/*` - 爬虫服务 API
  - [x] 保留 `/api/health` 健康检查路由（全局）

### 1.3 PPT 服务路由重构
- [x] 迁移 `app/api/tasks.py` 到 `app/api/ppt/router.py`
  - [x] 修改路由前缀为 `/ppt/tasks`
  - [x] 更新所有路由路径和标签
  - [x] 保持现有功能不变（轮询模式）
  
- [x] 迁移 `app/api/tasks_v2.py` 到 `app/api/ppt/router.py`
  - [x] 合并到同一个路由文件，使用不同端点（`/webhook` 端点）
  - [x] 修改路由前缀为 `/ppt/tasks`
  - [x] 保持 Webhook 模式功能
  
- [x] 迁移 `app/api/files.py` 到 `app/api/ppt/files.py`
  - [x] 修改路由前缀为 `/ppt/files`
  - [x] 确保文件上传功能正常

### 1.4 视频服务路由重构
- [x] 重构 `app/api/video.py` 到 `app/api/video/router.py`
  - [x] 修改路由前缀为 `/video/tasks`
  - [x] 更新所有路由路径和标签
  - [x] 更新下载链接路径（从 `/api/v1/video/tasks` 改为 `/api/video/tasks`）
  - [x] 保持现有功能不变

### 1.5 爬虫服务路由创建
- [x] 创建 `app/api/crawler/router.py`
  - [x] 定义爬虫任务创建接口 `POST /crawler/tasks`
  - [x] 定义爬虫任务查询接口 `GET /crawler/tasks/{task_id}`
  - [x] 定义爬虫任务列表接口 `GET /crawler/tasks`
  - [x] 定义爬虫任务删除接口 `DELETE /crawler/tasks/{task_id}`
  - [ ] 定义爬虫配置管理接口（可选，待实现）
  - [x] 定义爬虫结果下载接口 `GET /crawler/tasks/{task_id}/download`（框架已创建，功能待实现）

### 1.6 更新主应用路由
- [x] 修改 `app/main.py`
  - [x] 添加三个服务的页面路由：
    - [x] `GET /ppt` - 返回 `static/ppt/index.html`（支持向后兼容）
    - [x] `GET /video` - 返回 `static/video/index.html`（支持向后兼容）
    - [x] `GET /crawler` - 返回 `static/crawler/index.html`
  - [x] 修改根路径 `/` 为服务选择页面或重定向
  - [x] 保留 `/realtime`、`/tasks` 等旧路由（向后兼容，已标记为废弃）

---

## 🎨 二、前端 HTML 文件重构

### 2.1 创建前端目录结构
- [x] 创建 `static/ppt/` 目录
  - [x] `index.html` - PPT 服务主页面（从现有 index.html 迁移）
  - [ ] `tasks.html` - PPT 任务列表页面（从现有 tasks.html 迁移，可选，待实现）
  
- [x] 创建 `static/video/` 目录
  - [x] `index.html` - 视频服务主页面（从现有 video.html 迁移）
  
- [x] 创建 `static/crawler/` 目录
  - [x] `index.html` - 爬虫服务主页面（新建）
  - [ ] `tasks.html` - 爬虫任务列表页面（新建，可选，待实现）

- [x] 创建 `static/common/` 目录（共享资源）
  - [ ] `header.html` - 公共头部组件（可选，暂未实现）
  - [ ] `footer.html` - 公共底部组件（可选，暂未实现）
  - [ ] `api.js` - 统一的 API 调用封装（可选，暂未实现）
  - [ ] `websocket.js` - WebSocket 连接管理（可选，暂未实现）

### 2.2 PPT 服务前端重构
- [x] 迁移/重构 `static/index.html` 到 `static/ppt/index.html`
  - [x] 更新 API 调用路径为 `/api/ppt/tasks/webhook`（Webhook 模式）
  - [x] 更新下载路径为 `/api/ppt/tasks/{id}/download`
  - [x] 更新页面标题为 "PPT Generator Service"
  - [x] 更新导航链接（添加服务间导航）
  - [x] 更新 Logo 路径为 `/static/logo/logo.png`
  - [x] 确保所有功能正常

- [ ] 迁移 `static/tasks.html` 到 `static/ppt/tasks.html`（可选，待实现）
  - [ ] 更新 API 调用路径
  - [ ] 更新页面标题

### 2.3 视频服务前端重构
- [x] 迁移/重构 `static/video.html` 到 `static/video/index.html`
  - [x] 更新 API 调用路径为 `/api/video/tasks`（移除 v1 前缀）
  - [x] 更新下载路径为 `/api/video/tasks/{id}/download`
  - [x] 更新 Markdown 下载路径为 `/api/video/tasks/{id}/markdown`
  - [x] 更新页面标题为 "Video Generator Service"
  - [x] 更新导航链接（添加服务间导航）
  - [x] 更新 Logo 路径
  - [x] 确保所有功能正常

### 2.4 爬虫服务前端创建
- [x] 创建 `static/crawler/index.html`
  - [x] 设计爬虫任务创建表单
    - [x] URL 输入框
    - [x] 爬取深度选择（1-5）
    - [ ] 爬取规则配置（可选，待实现）
    - [x] 输出格式选择（JSON/CSV/Excel）
  - [x] 任务状态显示区域
  - [x] 任务列表展示
  - [x] 结果下载功能
  - [ ] 集成 WebSocket 实时更新（可选，待实现）
  - [x] API 调用路径：`/api/crawler/*`

### 2.5 创建服务导航页面
- [x] 创建 `static/index.html` 作为服务选择页面
  - [x] 三个服务的入口卡片
  - [x] 服务描述和功能说明
  - [x] 链接到 `/manus/ppt`、`/manus/video`、`/manus/crawler`
  - [x] 美观的 UI 设计

### 2.6 更新静态资源路径
- [x] 检查所有 HTML 文件中的静态资源路径
  - [x] CSS 文件路径（使用 CDN，无需更新）
  - [x] JavaScript 文件路径（使用 CDN，无需更新）
  - [x] 图片/Logo 路径（已更新为 `/static/logo/logo.png`）
  - [x] 确保路径正确（使用 `/static/` 绝对路径）

---

## 🕷️ 三、爬虫服务开发

### 3.1 创建爬虫服务模块
- [ ] 创建 `app/services/crawler/` 目录
  - [ ] `__init__.py` - 爬虫服务模块初始化
  - [ ] `crawler_service.py` - 爬虫核心服务类
  - [ ] `scheduler.py` - 爬虫任务调度器（可选）
  - [ ] `parser.py` - 内容解析器
  - [ ] `storage.py` - 结果存储管理

### 3.2 爬虫服务核心功能
- [ ] 实现 `CrawlerService` 类
  - [ ] 任务创建方法 `create_task()`
  - [ ] 任务执行方法 `execute_task()`
  - [ ] 任务状态查询方法 `get_task_status()`
  - [ ] 结果导出方法 `export_results()`
  - [ ] 错误处理和重试机制

- [ ] 实现爬虫引擎
  - [ ] HTTP 请求处理（使用 httpx）
  - [ ] HTML 解析（使用 BeautifulSoup 或 lxml）
  - [ ] 链接提取和去重
  - [ ] 深度控制
  - [ ] 并发控制（可选）

- [ ] 实现数据存储
  - [ ] JSON 格式存储
  - [ ] CSV 格式导出
  - [ ] Excel 格式导出（可选）
  - [ ] 存储到 `storage/crawler/` 目录

### 3.3 爬虫任务追踪
- [ ] 扩展 `TaskTrackerService` 或创建 `CrawlerTaskTracker`
  - [ ] 支持爬虫任务状态追踪
  - [ ] 存储爬虫配置和结果路径
  - [ ] 任务历史记录

### 3.4 爬虫配置管理
- [ ] 创建 `app/schemas/crawler.py`
  - [ ] `CrawlerTaskRequest` - 创建任务请求模型
  - [ ] `CrawlerTaskResponse` - 任务响应模型
  - [ ] `CrawlerConfig` - 爬虫配置模型
  - [ ] `CrawlerResult` - 爬虫结果模型

- [ ] 在 `app/config.py` 中添加爬虫配置
  - [ ] `crawler_storage_dir` - 爬虫结果存储目录
  - [ ] `crawler_max_depth` - 最大爬取深度
  - [ ] `crawler_timeout` - 请求超时时间
  - [ ] `crawler_concurrent_limit` - 并发限制（可选）

### 3.5 爬虫依赖安装
- [ ] 更新 `requirements.txt`
  - [ ] 添加 `beautifulsoup4>=4.12.0` - HTML 解析
  - [ ] 添加 `lxml>=4.9.0` - XML/HTML 解析器（可选，性能更好）
  - [ ] 添加 `pandas>=2.0.0` - 数据处理和 CSV/Excel 导出（可选）
  - [ ] 添加 `openpyxl>=3.1.0` - Excel 文件处理（如使用 pandas）

---

## 🔧 四、服务隔离和配置

### 4.1 WebSocket 路由更新
- [ ] 检查 `app/api/websocket.py`
  - [ ] 确保支持多服务 WebSocket 连接
  - [ ] 更新连接路径或添加服务标识
  - [ ] 确保消息路由正确（PPT/视频/爬虫）

### 4.2 Webhook 路由更新
- [ ] 检查 `app/api/webhook.py`
  - [ ] 确保 Webhook 回调能正确路由到对应服务
  - [ ] 添加服务类型标识（如需要）
  - [ ] 更新事件处理逻辑

### 4.3 依赖注入更新
- [ ] 检查 `app/dependencies.py`
  - [ ] 确保服务依赖正确注入
  - [ ] 添加爬虫服务依赖注入函数
  - [ ] 更新服务获取逻辑

### 4.4 异常处理
- [ ] 检查 `app/exceptions.py`
  - [ ] 确保异常处理覆盖所有服务
  - [ ] 添加爬虫服务特定异常（如需要）

---

## 📝 五、数据模型和 Schema

### 5.1 PPT 服务 Schema
- [ ] 检查 `app/schemas/task.py`
  - [ ] 确保所有模型适用于 PPT 服务
  - [ ] 添加服务类型标识（如需要）

### 5.2 视频服务 Schema
- [ ] 检查 `app/schemas/video.py`
  - [ ] 确保所有模型完整
  - [ ] 添加服务类型标识（如需要）

### 5.3 爬虫服务 Schema
- [ ] 创建 `app/schemas/crawler.py`
  - [ ] `CrawlerTaskRequest` - 创建任务请求
  - [ ] `CrawlerTaskResponse` - 任务响应
  - [ ] `CrawlerTaskStatus` - 任务状态枚举
  - [ ] `CrawlerConfig` - 爬虫配置
  - [ ] `CrawlerResult` - 爬虫结果

---

## 🧪 六、测试和验证

### 6.1 PPT 服务测试
- [ ] 测试 PPT 服务 API 路由
  - [ ] `/api/ppt/tasks` - 创建任务
  - [ ] `/api/ppt/tasks/{id}` - 查询任务
  - [ ] `/api/ppt/files` - 文件上传
- [ ] 测试 PPT 服务前端页面
  - [ ] `/manus/ppt` - 主页面加载
  - [ ] 功能交互测试

### 6.2 视频服务测试
- [ ] 测试视频服务 API 路由
  - [ ] `/api/video/tasks` - 创建任务
  - [ ] `/api/video/tasks/{id}` - 查询任务
- [ ] 测试视频服务前端页面
  - [ ] `/manus/video` - 主页面加载
  - [ ] 功能交互测试

### 6.3 爬虫服务测试
- [ ] 测试爬虫服务 API 路由
  - [ ] `/api/crawler/tasks` - 创建任务
  - [ ] `/api/crawler/tasks/{id}` - 查询任务
  - [ ] `/api/crawler/tasks/{id}/download` - 下载结果
- [ ] 测试爬虫服务前端页面
  - [ ] `/manus/crawler` - 主页面加载
  - [ ] 功能交互测试
- [ ] 端到端测试
  - [ ] 创建爬虫任务
  - [ ] 等待任务完成
  - [ ] 下载结果文件

### 6.4 集成测试
- [ ] 测试三个服务同时运行
- [ ] 测试 WebSocket 连接（如使用）
- [ ] 测试 Webhook 回调（如使用）
- [ ] 测试静态资源加载

---

## 📚 七、文档更新

### 7.1 API 文档
- [ ] 更新 API 文档路径
  - [ ] `/manus/docs` - 主 API 文档
  - [ ] 确保三个服务的 API 都正确显示
  - [ ] 添加服务标签分组

### 7.2 README 更新
- [ ] 更新 `readme.md`
  - [ ] 添加三服务架构说明
  - [ ] 更新服务访问地址
  - [ ] 添加爬虫服务使用说明
  - [ ] 更新部署说明

### 7.3 代码注释
- [ ] 为新创建的模块添加文档字符串
- [ ] 更新现有模块的注释（如需要）

---

## 🗂️ 八、文件清理（可选）

### 8.1 旧文件处理
- [ ] 标记废弃的文件
  - [ ] `app/api/tasks.py` - 已迁移到 `app/api/ppt/router.py`
  - [ ] `app/api/tasks_v2.py` - 已迁移到 `app/api/ppt/router.py`
  - [ ] `app/api/files.py` - 已迁移到 `app/api/ppt/files.py`
  - [ ] `app/api/video.py` - 已迁移到 `app/api/video/router.py`
  - [ ] `static/index.html` - 可能需要保留作为导航页
  - [ ] `static/video.html` - 已迁移到 `static/video/index.html`
  - [ ] `static/tasks.html` - 已迁移到 `static/ppt/tasks.html`（如需要）

- [ ] 决定是否删除或保留旧文件
  - [ ] 如果保留，添加废弃标记和迁移说明
  - [ ] 如果删除，确保所有引用已更新

---

## 🚀 九、部署准备

### 9.1 环境变量更新
- [ ] 检查 `.env.example`
  - [ ] 添加爬虫服务相关配置
  - [ ] 更新配置说明

### 9.2 存储目录
- [ ] 确保存储目录结构正确
  - [ ] `storage/output/` - PPT 输出
  - [ ] `storage/videos/` - 视频输出
  - [ ] `storage/crawler/` - 爬虫输出（新建）
  - [ ] `storage/tasks.json` - 任务追踪（或按服务分离）

### 9.3 启动脚本
- [ ] 检查 `run.py`
  - [ ] 确保能正常启动所有服务
  - [ ] 添加服务健康检查（可选）

---

## 📊 十、性能优化（可选）

### 10.1 路由优化
- [ ] 检查路由性能
- [ ] 添加路由缓存（如需要）

### 10.2 静态资源优化
- [ ] 检查静态资源加载
- [ ] 添加资源压缩（如需要）

### 10.3 爬虫性能优化
- [ ] 实现并发爬取（如需要）
- [ ] 添加请求限流
- [ ] 添加结果缓存（如需要）

---

## ✅ 完成检查清单

完成所有任务后，验证以下内容：

- [ ] 三个服务的前端页面都能正常访问
  - [ ] `https://ai.i5hn.com/manus/ppt`
  - [ ] `https://ai.i5hn.com/manus/video`
  - [ ] `https://ai.i5hn.com/manus/crawler`

- [ ] 三个服务的 API 都能正常调用
  - [ ] `/api/ppt/*`
  - [ ] `/api/video/*`
  - [ ] `/api/crawler/*`

- [ ] 所有功能正常工作
- [ ] 文档已更新
- [ ] 测试通过
- [ ] 代码已提交到版本控制

---

## 📌 注意事项

1. **向后兼容**：考虑是否需要保持旧路由的兼容性，或提供迁移指南
2. **错误处理**：确保每个服务都有完善的错误处理
3. **日志记录**：为每个服务添加适当的日志记录
4. **安全性**：确保爬虫服务有适当的访问控制和限流
5. **资源管理**：注意爬虫服务可能消耗较多资源，需要合理配置

---

**最后更新日期**: 2024-12-19
**预计完成时间**: 根据团队规模，建议分阶段完成，优先完成 PPT 和视频服务重构，再开发爬虫服务
