# 视频下载失败问题分析

## 问题描述

在 webhook 处理视频生成完成时，视频下载失败。从 `tasks.json` 中可以看到错误信息：
```
"error": "下载视频失败: object dict can't be used in 'await' expression"
```

## 已修复的问题

### 1. ✅ `get_task` 方法调用错误（已修复）

**问题**：在 `handle_video_generation_complete` 中使用了 `await self.tracker.get_task(local_task_id)`

**原因**：`get_task` 是同步方法，不能使用 `await`

**修复**：改为 `await self.tracker.get(local_task_id)`

**位置**：`app/services/video/generation_service.py:375`

### 2. ✅ 视频 URL 提取逻辑改进（已修复）

**问题**：视频 URL 提取逻辑可能无法正确处理 Manus API 返回的任务结果格式

**原因**：
- 没有检查 `message_type == "message"`（根据 Manus API 文档）
- 缺少对视频文件类型的判断（可能下载了非视频文件）
- 日志不够详细，难以调试

**修复**：
- 添加了 `message_type == "message"` 检查（与 `app/api/tasks.py` 中的逻辑一致）
- 改进了视频文件类型判断（通过 mimeType 和文件扩展名）
- 添加了详细的日志记录，包括完整的任务结果结构
- 添加了 URL 格式验证

**位置**：`app/services/video/generation_service.py:_download_video_file()`

## 可能的问题点

### 1. 视频 URL 提取失败

**代码位置**：`app/services/video/generation_service.py:_download_video_file()`

**当前逻辑**：
```python
# 从任务结果中提取视频文件 URL
outputs = task_result.get("output", task_result.get("outputs", []))

video_url = None
file_name = None

# 遍历 output 消息，查找文件类型的输出
for output in outputs:
    content = output.get("content", [])
    for item in content:
        item_type = item.get("type", "")
        if item_type == "output_file":
            url = item.get("fileUrl", item.get("url", item.get("file_url", "")))
            file_name = item.get("fileName", item.get("filename", ""))
            if url:
                video_url = url
                break
```

**可能的问题**：
1. **任务结果格式不匹配**：Manus API 返回的任务结果格式可能与预期不同
2. **output 结构不同**：`output` 可能是数组，也可能是对象
3. **content 结构不同**：`content` 可能不是数组，或者结构不同
4. **字段名不匹配**：`fileUrl`、`fileName` 等字段名可能不同

### 2. 任务结果获取时机问题

**代码位置**：`app/services/video/generation_service.py:399`

**当前逻辑**：
```python
video_task_result = await retry_async(
    lambda: self.task_manager.get_task(video_task_id),
    config=retry_config,
    operation_name="获取视频生成任务结果",
)
```

**可能的问题**：
1. **任务尚未完成**：webhook 触发时，任务结果可能还没有准备好
2. **重试次数不足**：虽然设置了 3 次重试，但可能还不够
3. **重试延迟太短**：初始延迟 1 秒可能太短

### 3. 视频文件下载失败

**代码位置**：`app/services/video/generation_service.py:764`

**当前逻辑**：
```python
async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
    response = await client.get(video_url)
    response.raise_for_status()
    # ...
```

**可能的问题**：
1. **URL 无效**：提取的 URL 可能无效或已过期
2. **需要认证**：URL 可能需要特殊的认证头
3. **超时**：300 秒超时可能不够
4. **网络问题**：下载过程中网络中断

### 4. 文件保存失败

**代码位置**：`app/services/video/generation_service.py:772`

**可能的问题**：
1. **目录不存在**：`video_storage_dir` 目录可能不存在
2. **权限问题**：没有写入权限
3. **磁盘空间不足**：存储空间已满

## 诊断建议

### 1. 添加详细日志

在关键位置添加日志，记录：
- 任务结果的完整结构
- 提取的 video_url
- 下载过程中的详细信息
- 错误堆栈

### 2. 检查任务结果格式

在 `_download_video_file` 方法开始时，记录完整的 `task_result`：
```python
logger.info(f"[视频下载] 任务结果结构: {json.dumps(task_result, indent=2, ensure_ascii=False)}")
```

### 3. 验证 URL 有效性

在下载前验证 URL：
```python
# 检查 URL 格式
if not video_url.startswith(('http://', 'https://')):
    raise RuntimeError(f"无效的视频 URL: {video_url}")
```

### 4. 增加重试和延迟

考虑增加重试次数和延迟：
```python
RetryConfig(
    max_retries=5,  # 增加到 5 次
    initial_delay=3.0,  # 初始延迟 3 秒
    max_delay=120.0,  # 最大延迟 120 秒
)
```

## 改进建议

### 1. 改进 URL 提取逻辑

支持多种任务结果格式：
```python
# 方法1：从 output 消息中提取
outputs = task_result.get("output", task_result.get("outputs", []))

# 方法2：从 files 字段提取
files = task_result.get("files", [])

# 方法3：从 result 字段提取
result = task_result.get("result", {})

# 方法4：从其他可能的字段提取
video_url = (
    task_result.get("output_url")
    or task_result.get("result_url")
    or task_result.get("download_url")
    or task_result.get("video_url")
)
```

### 2. 添加任务结果验证

在获取任务结果后，验证结果是否完整：
```python
if not video_task_result:
    raise RuntimeError("任务结果为空")

if video_task_result.get("status") != "finished":
    logger.warning(f"任务状态不是 finished: {video_task_result.get('status')}")
```

### 3. 改进错误处理

提供更详细的错误信息：
```python
try:
    # 下载逻辑
except httpx.HTTPError as e:
    logger.error(f"HTTP 错误: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
    logger.error(f"响应内容: {e.response.text if hasattr(e, 'response') else 'N/A'}")
    raise
```

### 4. 添加任务结果缓存

如果任务结果获取失败，可以稍后重试：
```python
# 保存任务 ID，稍后可以通过定时任务重试下载
await tracker.update(local_task_id, metadata={
    **metadata,
    "video_download_retry": True,
    "video_task_id": video_task_id,
})
```

## 调试步骤

1. **查看服务器日志**：检查 webhook 处理时的详细日志
2. **检查任务结果**：查看 Manus API 返回的完整任务结果
3. **验证 URL**：确认提取的 video_url 是否有效
4. **测试下载**：手动测试 video_url 是否可以下载
5. **检查存储**：确认存储目录存在且有写入权限

## 参考文档

- Manus API 文档：`manusdoc/docs/api-reference/get-task.md`
- 任务结果格式：查看 `app/api/tasks.py` 中的 `get_task_full_detail` 方法
