# 视频生成测试模式使用指南

## 功能说明

测试模式允许您使用历史数据回放视频生成流程，**无需调用真实的 Manus API**，完全免费测试前端功能。

## 如何使用

### 步骤 1：打开测试模式

1. 访问视频生成页面：`/manus/video` 或 `/video`
2. 在页面左侧找到 **"Test Mode (No API Cost)"** 区域
3. 点击右侧的开关，启用测试模式

### 步骤 2：选择历史任务

启用测试模式后，会显示：
- **Select Historical Task**：下拉列表，显示所有可回放的历史任务
- **Playback Speed**：回放速度选择（0.5x - 5.0x）

从下拉列表中选择一个任务（任务信息包括：主题、时长、风格、事件数量）

### 步骤 3：选择回放速度

- **0.5x (Slow)**：慢速回放，适合仔细观察
- **1.0x (Normal)**：正常速度（推荐）
- **2.0x (Fast)**：2倍速，快速测试
- **5.0x (Very Fast)**：5倍速，极速测试

### 步骤 4：开始回放

点击 **"Generate Video"** 按钮，系统会：
1. 连接到 WebSocket
2. 订阅任务更新
3. 开始回放历史数据
4. 在右侧 Timeline 中显示所有进度消息

### 步骤 5：观察 Timeline

Timeline 会按照历史数据的时间顺序显示：
- ✅ 脚本生成进度（`script_generation_progress`）
- ✅ 脚本生成完成（`script_generation_completed`）
- ✅ 视频生成开始（`video_generation_started`）
- ✅ 视频生成进度（`video_generation_progress`）
- ✅ 视频生成完成（`video_generation_completed`）

### 步骤 6：测试下载和播放

视频生成完成后，可以：
- 点击 **"Play Video"** 按钮在线播放（需要准备测试视频文件）
- 点击 **"Download"** 按钮下载视频（需要准备测试视频文件）

## 注意事项

### ⚠️ 重要提示

1. **WebSocket 连接**：确保 WebSocket 连接正常（右上角显示绿色 Connected）
2. **任务选择**：必须选择一个历史任务才能开始回放
3. **视频文件**：回放不会生成真实视频文件，下载功能需要后端配置测试视频文件
4. **数据来源**：历史任务数据来自 `output/tasks.json` 文件

### 🔧 技术细节

- **API 端点**：`POST /api/test/video/tasks/replay`
- **WebSocket 路径**：`/manus/ws/{client_id}`
- **消息格式**：与真实 API 完全一致
- **时间控制**：最小延迟 0.3 秒，最大延迟 5 秒

## 常见问题

### Q: 为什么看不到任务列表？
A: 检查 `output/tasks.json` 文件是否存在，并且包含视频生成任务（`task_type: "video_generation"`）

### Q: 回放速度太快/太慢？
A: 调整 **Playback Speed** 下拉菜单，选择合适的速度

### Q: Timeline 没有显示消息？
A: 
1. 检查 WebSocket 连接状态（右上角）
2. 确保已选择任务并点击了 Generate Video
3. 打开浏览器控制台查看错误信息

### Q: 可以同时回放多个任务吗？
A: 可以，但建议一次只回放一个任务，避免混淆

### Q: 测试模式会影响真实 API 吗？
A: 不会，测试模式完全独立，不会调用任何真实 API

## 开发调试

### 查看日志

打开浏览器开发者工具（F12），在 Console 中可以看到：
- WebSocket 连接状态
- 收到的消息
- 错误信息

### 检查网络请求

在 Network 标签中可以看到：
- `GET /api/test/video/tasks/available` - 获取任务列表
- `POST /api/test/video/tasks/replay` - 启动回放
- WebSocket 连接和消息

## 扩展功能

如果需要添加更多测试功能，可以：
1. 修改 `app/api/test/router.py` 添加新的测试端点
2. 修改 `static/video/app.js` 添加新的前端功能
3. 准备测试视频文件，放在 `static/test/` 目录
