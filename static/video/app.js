// Video Generator Service - Main Application Script
// /manus 子路径部署适配：自动推断 base path
const APP_BASE = window.location.pathname.startsWith('/manus') ? '/manus' : '';
const API_BASE = `${APP_BASE}/api`;
let currentTaskId = null;
let clientId = null;
let ws = null;
let wsReconnectTimer = null;
let videoDownloadUrl = null;  // 视频下载/播放 URL
let testMode = false;  // 测试模式开关

// 样式图标映射
const styleIcons = {
    'educational': 'graduation-cap',
    'promotional': 'bullhorn',
    'documentary': 'film',
    'tutorial': 'book',
    'corporate': 'briefcase'
};

// 更新样式选择框图标
function updateStyleIcon() {
    const select = document.getElementById('styleSelect');
    const icon = document.getElementById('styleSelectIcon');
    if (!select || !icon) return;
    
    const selectedValue = select.value;
    const iconName = styleIcons[selectedValue] || 'film';
    icon.className = `fa fa-${iconName} absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none`;
}

// 显示 Activity Timeline 面板（带动画）
function showTimelinePanel() {
    const panel = document.getElementById('timelinePanel');
    const leftArea = document.getElementById('leftContentArea');
    
    if (panel && !panel.classList.contains('show')) {
        // 先缩小左侧区域
        if (leftArea) {
            leftArea.classList.add('compact');
        }
        
        // 然后显示右侧 Timeline 面板（稍微延迟，让左侧动画先开始）
        setTimeout(() => {
            panel.classList.add('show');
        }, 100);
    }
}

// 多组示例主题
const exampleTopicsGroups = [
    [
        'Introduction to Artificial Intelligence',
        'How to Start a Successful Business',
        'Climate Change and Its Impact',
        'The Future of Remote Work'
    ],
    [
        'Understanding Machine Learning Basics',
        'Digital Marketing Strategies for 2024',
        'Sustainable Energy Solutions',
        'Effective Team Communication'
    ],
    [
        'Cybersecurity Best Practices',
        'Personal Finance Management',
        'Healthy Lifestyle Tips',
        'Innovation in Technology'
    ],
    [
        'Leadership Development Skills',
        'Productivity Hacks for Professionals',
        'Social Media Marketing Guide',
        'Mental Health Awareness'
    ],
    [
        'Data Science Fundamentals',
        'Entrepreneurship Essentials',
        'Environmental Conservation',
        'Career Development Strategies'
    ]
];

let currentTopicsGroupIndex = 0;

// 渲染示例主题
function renderExampleTopics() {
    const container = document.getElementById('examplePromptsContainer');
    if (!container) return;
    
    const topics = exampleTopicsGroups[currentTopicsGroupIndex];
    container.innerHTML = topics.map(topic => {
        // 转义单引号，避免 onclick 中的引号冲突
        const escapedTopic = topic.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
            <div class="bg-white rounded-xl shadow-soft p-4 card-hover cursor-pointer" onclick="fillExample('${escapedTopic}')">
                <p class="text-gray-700 text-sm">${topic}</p>
            </div>
        `;
    }).join('');
}

// 刷新示例主题（切换到下一组）
window.refreshExamplePrompts = function() {
    currentTopicsGroupIndex = (currentTopicsGroupIndex + 1) % exampleTopicsGroups.length;
    renderExampleTopics();
    
    // 添加旋转动画
    const refreshBtn = document.getElementById('refreshPromptsBtn');
    if (refreshBtn) {
        const icon = refreshBtn.querySelector('i');
        if (icon) {
            icon.style.transition = 'transform 0.5s ease';
            icon.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                icon.style.transform = 'rotate(0deg)';
            }, 500);
        }
    }
};

// 填充示例主题（全局函数，供 onclick 调用）
window.fillExample = function(text) {
    const topicInput = document.getElementById('topicInput');
    if (topicInput) {
        topicInput.value = text;
    }
    // 清除错误消息
    const errorDiv = document.getElementById('topicError');
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
};

// 初始化 WebSocket 连接
function initWebSocket() {
    clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${APP_BASE}/ws/${clientId}`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateWSStatus(true, 'Connected');
        
        // 发送订阅消息
        if (currentTaskId) {
            ws.send(JSON.stringify({
                action: 'subscribe',
                task_id: currentTaskId
            }));
        }
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('WebSocket message parse error:', e);
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateWSStatus(false, 'Connection error');
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateWSStatus(false, 'Disconnected');
        
        // 尝试重连
        if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
        wsReconnectTimer = setTimeout(() => {
            initWebSocket();
        }, 3000);
    };
}

// 更新 WebSocket 状态显示
function updateWSStatus(connected, text) {
    const indicator = document.getElementById('wsIndicator');
    const statusText = document.getElementById('wsStatusText');
    
    if (indicator && statusText) {
        if (connected) {
            indicator.className = 'w-2 h-2 rounded-full bg-green-500';
        } else {
            indicator.className = 'w-2 h-2 rounded-full bg-red-500';
        }
        statusText.textContent = text;
    }
}

// 处理 WebSocket 消息
function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);
    
    switch (data.type) {
        case 'connected':
            updateWSStatus(true, 'Connected');
            break;
            
        case 'script_generation_progress':
        case 'video_generation_progress':
            const progressMsg = data.message || 'Processing...';
            addTimelineItem('progress', 'Task Progress', progressMsg, data.timestamp);
            break;
            
        case 'script_generation_completed':
            addTimelineItem('completed', 'Script Completed', 'Script generation completed', data.timestamp);
            if (data.video_task_id) {
                // 订阅视频生成任务
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        action: 'subscribe',
                        task_id: data.video_task_id
                    }));
                }
            }
            break;
            
        case 'video_generation_started':
            addTimelineItem('progress', 'Video Generation', 'Video generation started', data.timestamp);
            break;
            
        case 'video_generation_completed':
            // 先更新所有 progress 项为 completed，移除光影效果
            updateTimelineItemStatus('completed');
            addTimelineItem('completed', 'Task Completed', 'Video generation completed!', data.timestamp);
            if (data.local_task_id) {
                currentTaskId = data.local_task_id;
            }
            
            // 保存视频下载 URL（用于播放和下载）
            if (data.download_url) {
                videoDownloadUrl = data.download_url.startsWith('http') ? data.download_url : `${APP_BASE}${data.download_url}`;
            } else if (currentTaskId) {
                videoDownloadUrl = `${API_BASE}/video/tasks/${currentTaskId}/download`;
            }
            
            // 设置视频播放器源（使用 inline=true 参数以支持在线播放）
            const videoPlayer = document.getElementById('videoPlayer');
            const videoPlayerContainer = document.getElementById('videoPlayerContainer');
            if (videoPlayer && videoDownloadUrl) {
                // 将下载 URL 转换为播放 URL（添加 inline=true 参数）
                const playUrl = videoDownloadUrl.includes('?') 
                    ? `${videoDownloadUrl}&inline=true` 
                    : `${videoDownloadUrl}?inline=true`;
                videoPlayer.src = playUrl;
                // 视频加载完成后显示播放器
                videoPlayer.onloadedmetadata = () => {
                    if (videoPlayerContainer) {
                        videoPlayerContainer.classList.remove('hidden');
                    }
                };
                // 处理加载错误
                videoPlayer.onerror = (e) => {
                    console.error('视频加载失败:', e);
                    if (videoPlayerContainer) {
                        videoPlayerContainer.classList.add('hidden');
                    }
                };
            }
            
            document.getElementById('downloadSection').classList.remove('hidden');
            document.getElementById('generateBtn').disabled = false;
            document.getElementById('generateBtnText').textContent = 'Generate New Video';
            break;
            
        case 'script_generation_failed':
        case 'video_generation_failed':
        case 'task_failed':
            // 先更新所有 progress 项为 error，移除光影效果
            updateTimelineItemStatus('error');
            addTimelineItem('error', 'Task Failed', data.error || 'Task failed', data.timestamp);
            document.getElementById('generateBtn').disabled = false;
            document.getElementById('generateBtnText').textContent = 'Retry';
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

// 移除所有 progress 项的光影效果（移除 active 类）
function removeAllProgressEffects() {
    const container = document.getElementById('timelineContainer');
    if (!container) return;
    
    const progressItems = container.querySelectorAll('.timeline-item.progress.active');
    progressItems.forEach(item => {
        item.classList.remove('active');
    });
}

// 更新时间轴项状态（从 progress 变为 completed 或 error，移除光影效果）
function updateTimelineItemStatus(newType) {
    const container = document.getElementById('timelineContainer');
    if (!container) return;
    
    const progressItems = container.querySelectorAll('.timeline-item.progress');
    
    progressItems.forEach(item => {
        // 移除 progress 类、active 类和相关动画
        item.classList.remove('progress', 'active');
        item.classList.add(newType);
        item.style.animation = 'none';
    });
}

// 添加时间轴项目
function addTimelineItem(type, title, message, timestamp, options = {}) {
    const container = document.getElementById('timelineContainer');
    const emptyMsg = document.getElementById('emptyTimeline');
    
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    // 如果新项是 progress，先移除之前所有 progress 项的光影效果
    if (type === 'progress') {
        removeAllProgressEffects();
    }
    
    // 如果新项是 completed 或 error，移除之前所有 progress 项的光影效果并更新状态
    if (type === 'completed' || type === 'error') {
        updateTimelineItemStatus(type);
    }
    
    const item = document.createElement('div');
    item.className = `timeline-item ${type}`;
    
    // 如果是 progress 类型，添加 active 类以显示光影效果
    if (type === 'progress') {
        item.classList.add('active');
    }
    
    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    
    // 构建内容 HTML
    let contentHtml = `
        <div class="bg-gray-50 rounded-lg p-3">
            <div class="flex items-center justify-between mb-1">
                <h4 class="text-sm font-semibold text-gray-900">${title}</h4>
                <span class="text-xs text-gray-500">${time}</span>
            </div>
            <p class="text-xs text-gray-600">${message}</p>
    `;
    
    // 如果包含视频，添加视频播放器
    if (options.showVideo && options.videoUrl) {
        // 确保视频 URL 包含 inline=true 参数以支持在线播放
        let playUrl = options.videoUrl;
        if (!playUrl.includes('inline=true')) {
            playUrl = playUrl.includes('?') 
                ? `${playUrl}&inline=true` 
                : `${playUrl}?inline=true`;
        }
        contentHtml += `
            <div class="mt-3 rounded-lg overflow-hidden bg-black">
                <video 
                    controls 
                    class="w-full max-h-64"
                    preload="metadata"
                    style="max-height: 256px;"
                >
                    <source src="${playUrl}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
        `;
    }
    
    contentHtml += `</div>`;
    
    item.innerHTML = contentHtml;
    
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

// 生成视频（全局函数，供 onclick 调用）
window.generateVideo = async function() {
    // 检查是否是测试模式
    if (testMode) {
        const taskSelect = document.getElementById('testTaskSelect');
        const speedSelect = document.getElementById('testSpeedSelect');
        const selectedTaskId = taskSelect ? taskSelect.value : '';
        const speed = speedSelect ? speedSelect.value : '1.0';
        
        if (!selectedTaskId) {
            alert('Please select a task to replay in test mode');
            return;
        }
        
        await replayTask(selectedTaskId, speed);
        return;
    }
    
    // 正常模式：生成新视频
    const topic = document.getElementById('topicInput').value.trim();
    const duration = parseInt(document.getElementById('durationSelect').value);
    const style = document.getElementById('styleSelect').value;
    const audience = document.getElementById('audienceSelect').value;
    const errorDiv = document.getElementById('topicError');
    
    // 验证输入
    if (!topic) {
        if (errorDiv) {
            errorDiv.textContent = 'Please enter a video topic';
            errorDiv.classList.remove('hidden');
        }
        return;
    }
    
    // 清除错误消息
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
    
    // 显示 Activity Timeline 面板（带动画）
    showTimelinePanel();
    
    // 禁用按钮
    const generateBtn = document.getElementById('generateBtn');
    const generateBtnText = document.getElementById('generateBtnText');
    if (generateBtn) {
        generateBtn.disabled = true;
    }
    if (generateBtnText) {
        generateBtnText.textContent = 'Generating...';
    }
    
    // 清空时间轴
    const timelineContainer = document.getElementById('timelineContainer');
    if (timelineContainer) {
        timelineContainer.innerHTML = '<div class="text-center text-gray-400 text-sm py-8" id="emptyTimeline">No activity yet. Start generating to see progress.</div>';
    }
    document.getElementById('downloadSection').classList.add('hidden');
    
    // 隐藏视频播放器并重置
    const videoPlayerContainer = document.getElementById('videoPlayerContainer');
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayerContainer) {
        videoPlayerContainer.classList.add('hidden');
    }
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    
    // 重置视频下载 URL
    videoDownloadUrl = null;
    
    // 添加初始时间轴项
    addTimelineItem('progress', 'Starting', 'Creating task...', new Date().toISOString());
    
    try {
        // 创建任务（使用 Video 服务 API）
        const response = await fetch(`${API_BASE}/video/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic: topic,
                duration: duration,
                style: style,
                target_audience: audience,
                client_id: clientId
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Failed to create task');
        }
        
        currentTaskId = result.data.task_id;
        
        // 订阅任务更新
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'subscribe',
                task_id: currentTaskId
            }));
        }
        
        addTimelineItem('progress', 'Task Created', `Task ID: ${currentTaskId.slice(0, 8)}...`, new Date().toISOString());
        
    } catch (error) {
        console.error('Error creating task:', error);
        addTimelineItem('error', 'Error', error.message || 'Failed to create task', new Date().toISOString());
        if (generateBtn) {
            generateBtn.disabled = false;
        }
        if (generateBtnText) {
            generateBtnText.textContent = 'Retry';
        }
    }
};

// 播放视频（全局函数，供 onclick 调用）
window.playVideo = function() {
    const videoPlayer = document.getElementById('videoPlayer');
    const videoPlayerContainer = document.getElementById('videoPlayerContainer');
    
    if (videoPlayer && currentTaskId) {
        // 如果视频源还没有设置，设置它（使用 inline=true 参数以支持在线播放）
        if (!videoPlayer.src || videoPlayer.src === window.location.href || !videoPlayer.src.includes('download')) {
            const videoUrl = `${API_BASE}/video/tasks/${currentTaskId}/download?inline=true`;
            videoPlayer.src = videoUrl;
        }
        
        // 显示播放器
        if (videoPlayerContainer) {
            videoPlayerContainer.classList.remove('hidden');
        }
        
        // 播放视频
        videoPlayer.play().catch(e => {
            console.error('播放视频失败:', e);
            alert('播放视频失败，请尝试下载后播放');
        });
    }
};

// 播放视频（全局函数，供 onclick 调用）
window.playVideo = function() {
    const videoPlayer = document.getElementById('videoPlayer');
    const videoPlayerContainer = document.getElementById('videoPlayerContainer');
    
    if (videoPlayer && (videoDownloadUrl || currentTaskId)) {
        // 确定视频 URL
        let videoUrl;
        if (videoDownloadUrl) {
            // 将下载 URL 转换为播放 URL（添加 inline=true 参数）
            videoUrl = videoDownloadUrl.includes('?') 
                ? `${videoDownloadUrl}&inline=true` 
                : `${videoDownloadUrl}?inline=true`;
        } else if (currentTaskId) {
            videoUrl = `${API_BASE}/video/tasks/${currentTaskId}/download?inline=true`;
        }
        
        // 如果视频源还没有设置，设置它
        if (!videoPlayer.src || !videoPlayer.src.includes('download')) {
            videoPlayer.src = videoUrl;
        }
        
        // 显示播放器
        if (videoPlayerContainer) {
            videoPlayerContainer.classList.remove('hidden');
        }
        
        // 播放视频
        videoPlayer.play().catch(e => {
            console.error('播放视频失败:', e);
            alert('播放视频失败，请尝试下载后播放');
        });
    }
};

// 检查任务是否有视频文件
async function checkTaskVideoAvailable(taskId) {
    try {
        const response = await fetch(`${API_BASE}/video/tasks/${taskId}`);
        const result = await response.json();
        if (result.success && result.data) {
            return !!result.data.video_url;
        }
        return false;
    } catch (error) {
        console.error('检查任务视频失败:', error);
        return false;
    }
}

// 下载视频（全局函数，供 onclick 调用）
window.downloadVideo = async function() {
    if (!currentTaskId) {
        alert('没有可下载的视频');
        return;
    }
    
    // 检查是否有视频文件
    const hasVideo = await checkTaskVideoAvailable(currentTaskId);
    if (!hasVideo && testMode) {
        alert('测试模式：此历史任务没有视频文件。如果需要测试下载功能，请准备测试视频文件放在 static/test/sample_video.mp4');
        return;
    }
    
    if (videoDownloadUrl) {
        window.open(videoDownloadUrl, '_blank');
    } else if (currentTaskId) {
        window.open(`${API_BASE}/video/tasks/${currentTaskId}/download`, '_blank');
    }
};

// 切换测试模式
window.toggleTestMode = function() {
    const toggle = document.getElementById('testModeToggle');
    const panel = document.getElementById('testModePanel');
    testMode = toggle.checked;
    
    if (testMode) {
        panel.classList.remove('hidden');
        loadReplayableTasks();
    } else {
        panel.classList.add('hidden');
    }
};

// 加载可回放的任务列表
async function loadReplayableTasks() {
    const select = document.getElementById('testTaskSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Loading tasks...</option>';
    
    try {
        const response = await fetch(`${API_BASE}/test/video/tasks/available`);
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            select.innerHTML = '<option value="">Select a task to replay...</option>';
            result.data.forEach(task => {
                const option = document.createElement('option');
                option.value = task.task_id;
                option.textContent = `${task.topic} (${task.duration}s, ${task.style}) - ${task.event_count} events`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">No replayable tasks found</option>';
        }
    } catch (error) {
        console.error('Failed to load replayable tasks:', error);
        select.innerHTML = '<option value="">Error loading tasks</option>';
    }
}

// 回放历史任务
async function replayTask(taskId, speed) {
    if (!taskId) {
        alert('Please select a task to replay');
        return;
    }
    
    // 显示 Activity Timeline 面板
    showTimelinePanel();
    
    // 禁用按钮
    const generateBtn = document.getElementById('generateBtn');
    const generateBtnText = document.getElementById('generateBtnText');
    if (generateBtn) {
        generateBtn.disabled = true;
    }
    if (generateBtnText) {
        generateBtnText.textContent = 'Replaying...';
    }
    
    // 清空时间轴
    const timelineContainer = document.getElementById('timelineContainer');
    if (timelineContainer) {
        timelineContainer.innerHTML = '<div class="text-center text-gray-400 text-sm py-8" id="emptyTimeline">Starting replay...</div>';
    }
    document.getElementById('downloadSection').classList.add('hidden');
    
    // 隐藏视频播放器并重置
    const videoPlayerContainer = document.getElementById('videoPlayerContainer');
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayerContainer) {
        videoPlayerContainer.classList.add('hidden');
    }
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    
    // 重置视频下载 URL
    videoDownloadUrl = null;
    
    try {
        // 调用回放 API
        const response = await fetch(`${API_BASE}/test/video/tasks/replay`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                task_id: taskId,
                client_id: clientId,
                speed: parseFloat(speed) || 1.0
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Failed to start replay');
        }
        
        currentTaskId = result.local_task_id;
        
        // 订阅任务更新
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                action: 'subscribe',
                task_id: currentTaskId
            }));
            // 也订阅 script_task_id 和 video_task_id
            if (result.script_task_id) {
                ws.send(JSON.stringify({
                    action: 'subscribe',
                    task_id: result.script_task_id
                }));
            }
            if (result.video_task_id) {
                ws.send(JSON.stringify({
                    action: 'subscribe',
                    task_id: result.video_task_id
                }));
            }
        }
        
        addTimelineItem('progress', 'Replay Started', `Replaying task: ${taskId.slice(0, 8)}... (${result.total_events} events, ~${Math.round(result.estimated_duration)}s)`, new Date().toISOString());
        
    } catch (error) {
        console.error('Error starting replay:', error);
        addTimelineItem('error', 'Error', error.message || 'Failed to start replay', new Date().toISOString());
        if (generateBtn) {
            generateBtn.disabled = false;
        }
        if (generateBtnText) {
            generateBtnText.textContent = 'Retry';
        }
    }
}

// 初始化函数
function initApp() {
    // 初始化样式图标
    updateStyleIcon();
    
    // 渲染示例主题
    renderExampleTopics();
    
    // 当用户输入 topicInput 时，清空错误消息
    const topicInput = document.getElementById('topicInput');
    if (topicInput) {
        topicInput.addEventListener('input', () => {
            const errorDiv = document.getElementById('topicError');
            if (errorDiv) {
                errorDiv.classList.add('hidden');
            }
        });
    }
    
    // 样式选择框图标更新
    const styleSelect = document.getElementById('styleSelect');
    if (styleSelect) {
        styleSelect.addEventListener('change', updateStyleIcon);
    }
    
    // 初始化 WebSocket 连接
    initWebSocket();
}

// 初始化：检查文档是否已加载完成
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    // 文档已经加载完成，直接执行初始化
    setTimeout(initApp, 0);
}
