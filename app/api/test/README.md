# 测试 API - 历史数据回放

## 功能说明

基于 `tasks.json` 中的历史数据，回放视频生成任务的完整流程，通过 WebSocket 发送消息给前端，模拟真实的视频生成过程。

**优势**：
- ✅ 无需调用真实的 Manus API（节省费用）
- ✅ 完全模拟真实流程
- ✅ 支持速度控制
- ✅ 基于真实历史数据

## API 端点

### 1. 获取可回放的任务列表

```
GET /api/test/video/tasks/available
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "task_id": "f5322eb7-4d17-43ae-a664-062e809a278c",
      "topic": "Productivity Hacks for Professionals",
      "duration": 15,
      "style": "educational",
      "target_audience": "general",
      "status": "failed",
      "event_count": 10,
      "created_at": "2026-01-21T03:50:19.021419"
    }
  ],
  "total": 1
}
```

### 2. 回放历史任务

```
POST /api/test/video/tasks/replay
```

**请求体**：
```json
{
  "task_id": "f5322eb7-4d17-43ae-a664-062e809a278c",
  "client_id": "client_xxx",  // 可选，WebSocket 客户端 ID
  "speed": 2.0,  // 可选，回放速度（1.0 = 正常速度，2.0 = 2倍速）
  "local_task_id": "xxx"  // 可选，如果已存在本地任务
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "回放任务已启动",
  "local_task_id": "f5322eb7-4d17-43ae-a664-062e809a278c",
  "script_task_id": "bdeczjbvaP5rEPRAMjadZu",
  "video_task_id": "oNf4ufdv9kedCbCtMqKGRD",
  "total_events": 10,
  "estimated_duration": 45.5
}
```

## 使用流程

### 方式1：通过前端调用（推荐）

1. **前端连接 WebSocket**
   ```javascript
   const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
   const ws = new WebSocket(`ws://host/manus/ws/${clientId}`);
   ```

2. **获取可回放的任务列表**
   ```javascript
   const response = await fetch('/api/test/video/tasks/available');
   const data = await response.json();
   console.log('可回放的任务:', data.data);
   ```

3. **启动回放**
   ```javascript
   const replayResponse = await fetch('/api/test/video/tasks/replay', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       task_id: 'f5322eb7-4d17-43ae-a664-062e809a278c',
       client_id: clientId,
       speed: 2.0  // 2倍速回放
     })
   });
   const result = await replayResponse.json();
   const localTaskId = result.local_task_id;
   ```

4. **订阅任务更新**
   ```javascript
   ws.send(JSON.stringify({
     action: 'subscribe',
     task_id: localTaskId
   }));
   ```

5. **接收 WebSocket 消息**
   ```javascript
   ws.onmessage = (event) => {
     const data = JSON.parse(event.data);
     console.log('收到消息:', data);
     // 前端会自动处理这些消息，更新 timeline
   };
   ```

### 方式2：直接使用 curl

```bash
# 1. 获取可回放的任务列表
curl http://localhost:8000/api/test/video/tasks/available

# 2. 启动回放（需要先连接 WebSocket 并订阅任务）
curl -X POST http://localhost:8000/api/test/video/tasks/replay \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "f5322eb7-4d17-43ae-a664-062e809a278c",
    "speed": 1.0
  }'
```

## 消息流程

回放会按照以下顺序发送 WebSocket 消息：

1. **脚本生成阶段**：
   - `script_generation_progress` (多次)
   - `script_generation_completed` (包含 `video_task_id`)

2. **视频生成阶段**：
   - `video_generation_started`
   - `video_generation_progress` (多次)
   - `video_generation_completed` (包含 `download_url`)

## 注意事项

1. **WebSocket 连接**：前端必须先连接 WebSocket 并订阅 `local_task_id`，才能收到消息

2. **任务订阅**：前端在收到 `script_generation_completed` 消息后，会自动订阅 `video_task_id`

3. **速度控制**：
   - `speed = 1.0`：正常速度（按照原始时间间隔）
   - `speed = 2.0`：2倍速（时间间隔减半）
   - `speed = 0.5`：0.5倍速（时间间隔加倍）
   - 最小延迟：0.3 秒（避免消息发送过快）
   - 最大延迟：5 秒（避免等待时间过长）

4. **任务状态**：回放完成后，任务状态会自动更新为 `completed`

5. **视频文件**：回放不会生成真实的视频文件，但会设置正确的 `download_url`。如果需要测试下载功能，需要准备一个测试视频文件。

## 扩展功能

### 添加测试视频文件

如果需要测试视频下载功能，可以：

1. 准备一个测试视频文件（如 `static/test/sample_video.mp4`）
2. 在回放完成后，将测试文件复制到任务目录
3. 更新任务的 `metadata.video_path`

或者修改 `app/api/video/router.py` 的下载端点，在测试模式下返回测试视频文件。
