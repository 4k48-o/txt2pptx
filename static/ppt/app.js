// PPT Generator Service - Main Application Script
// /manus 子路径部署适配：自动推断 base path
const APP_BASE = window.location.pathname.startsWith('/manus') ? '/manus' : '';
const API_BASE = `${APP_BASE}/api`;
let currentTaskId = null;
let clientId = null;
let ws = null;
let wsReconnectTimer = null;

// 样式图标映射
const styleIcons = {
    'professional': 'briefcase',
    'modern': 'star',
    'creative': 'paint-brush',
    'academic': 'graduation-cap',
    'tech': 'laptop',
    'elegant': 'heart'
};

// 更新样式选择框图标
function updateStyleIcon() {
    const select = document.getElementById('styleSelect');
    const icon = document.getElementById('styleSelectIcon');
    const selectedValue = select.value;
    const iconName = styleIcons[selectedValue] || 'star';
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

// 多组示例提示词
const examplePromptsGroups = [
    [
        'Create a training module on cybersecurity best practices',
        'Build a sales presentation for B2B software solutions',
        'Design a presentation on tech impact on future jobs',
        'Create a startup pitch deck for fundraising'
    ],
    [
        'Develop a quarterly business review presentation',
        'Create an onboarding presentation for new employees',
        'Design a product launch presentation for a new app',
        'Build a financial report presentation for stakeholders'
    ],
    [
        'Create a marketing strategy presentation for Q4',
        'Design a training presentation on customer service excellence',
        'Build a project proposal presentation for a new initiative',
        'Create a company culture and values presentation'
    ],
    [
        'Develop a data analytics insights presentation',
        'Design a sustainability and ESG report presentation',
        'Create a competitive analysis presentation',
        'Build a team building and collaboration workshop presentation'
    ],
    [
        'Create a technology trends and innovation presentation',
        'Design a customer success stories presentation',
        'Build a process improvement and optimization presentation',
        'Create a leadership development program presentation'
    ]
];

let currentPromptsGroupIndex = 0;

// 渲染示例提示词
function renderExamplePrompts() {
    const container = document.getElementById('examplePromptsContainer');
    if (!container) return;
    
    const prompts = examplePromptsGroups[currentPromptsGroupIndex];
    container.innerHTML = prompts.map(prompt => {
        // 转义单引号，避免 onclick 中的引号冲突
        const escapedPrompt = prompt.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
            <div class="bg-white rounded-xl shadow-soft p-4 card-hover cursor-pointer" onclick="fillExample('${escapedPrompt}')">
                <p class="text-gray-700 text-sm">${prompt}</p>
            </div>
        `;
    }).join('');
}

// 刷新示例提示词（切换到下一组）
window.refreshExamplePrompts = function() {
    currentPromptsGroupIndex = (currentPromptsGroupIndex + 1) % examplePromptsGroups.length;
    renderExamplePrompts();
    
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

// 填充示例提示词（全局函数，供 onclick 调用）
window.fillExample = function(text) {
    document.getElementById('promptInput').value = text;
};

// 生成 PPT（全局函数，供 onclick 调用）
window.generatePPT = async function() {
    const prompt = document.getElementById('promptInput').value.trim();
    const slides = document.getElementById('slidesSelect').value;
    const style = document.getElementById('styleSelect').value;
    const audience = document.getElementById('audienceSelect').value;
    const customAudience = document.getElementById('customAudienceText').value.trim();
    
    if (!prompt) {
        // 显示错误消息
        const errorDiv = document.getElementById('promptError');
        if (errorDiv) {
            errorDiv.classList.remove('hidden');
        }
        return;
    }
    
    // 清空错误消息（如果有）
    const errorDiv = document.getElementById('promptError');
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
    
    // 显示 Activity Timeline 面板（带动画）
    showTimelinePanel();
    
    // 构建完整的提示词
    let fullPrompt = prompt;
    
    // 添加页数
    fullPrompt += `, generate ${slides} slides`;
    
    // 添加样式
    const styleNames = {
        'professional': 'professional business style',
        'modern': 'modern minimalist style',
        'creative': 'creative artistic style',
        'academic': 'academic report style',
        'tech': 'tech-focused style',
        'elegant': 'elegant and fresh style'
    };
    fullPrompt += `, use ${styleNames[style]}`;
    
    // 添加目标人群
    const finalAudience = audience === 'custom' ? customAudience : audience;
    if (finalAudience) {
        fullPrompt += `, target audience: ${finalAudience}`;
    }
    
    // 禁用按钮
    document.getElementById('generateBtn').disabled = true;
    document.getElementById('generateBtnText').textContent = 'Generating...';
    
    // 清空时间轴
    document.getElementById('timelineContainer').innerHTML = '<div class="text-center text-gray-400 text-sm py-8" id="emptyTimeline">No activity yet. Start generating to see progress.</div>';
    document.getElementById('downloadSection').classList.add('hidden');
    
    // 添加初始时间轴项
    addTimelineItem('progress', 'Starting', 'Creating task...', new Date().toISOString());
    
    try {
        // 创建任务（使用 PPT 服务 Webhook API）
        const response = await fetch(`${API_BASE}/ppt/tasks/webhook`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                prompt: fullPrompt,
                client_id: clientId
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Failed to create task');
        }
        
        currentTaskId = result.data.id;
        
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
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('generateBtnText').textContent = 'Retry';
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
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
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
    
    if (connected) {
        indicator.className = 'w-2 h-2 rounded-full bg-green-500';
    } else {
        indicator.className = 'w-2 h-2 rounded-full bg-red-500';
    }
    statusText.textContent = text;
}

// 处理 WebSocket 消息
function handleWebSocketMessage(message) {
    console.log('WebSocket message:', message);
    
    switch (message.type) {
        case 'connected':
            updateWSStatus(true, 'Connected');
            break;
            
        case 'task_update':
        case 'task_progress':
            const progressMsg = message.data?.message || message.message || 'Processing...';
            addTimelineItem('progress', 'Task Progress', progressMsg, message.timestamp);
            break;
            
        case 'task_created':
            const createdMsg = message.message || `Task created: ${message.title || message.task_id || 'Task'}`;
            addTimelineItem('progress', 'Task Created', createdMsg, message.timestamp);
            if (message.task_id) {
                currentTaskId = message.local_task_id || message.task_id;
            }
            break;
            
        case 'task_completed':
            // 先更新所有 progress 项为 completed，移除光影效果
            updateTimelineItemStatus('completed');
            const completedMsg = message.message || 'PPT generation completed successfully!';
            addTimelineItem('completed', 'Task Completed', completedMsg, message.timestamp);
            if (message.local_task_id) {
                currentTaskId = message.local_task_id;
            }
            document.getElementById('downloadSection').classList.remove('hidden');
            document.getElementById('generateBtn').disabled = false;
            document.getElementById('generateBtnText').textContent = 'Generate New PPT';
            break;
            
        case 'task_failed':
            // 先更新所有 progress 项为 error，移除光影效果
            updateTimelineItemStatus('error');
            addTimelineItem('error', 'Task Failed', message.error || 'Task failed', message.timestamp);
            document.getElementById('generateBtn').disabled = false;
            document.getElementById('generateBtnText').textContent = 'Retry';
            break;
            
        case 'pong':
            // 心跳响应，忽略
            break;
            
        default:
            console.log('Unknown message type:', message.type);
    }
}

// 移除所有 progress 项的光影效果（移除 active 类）
function removeAllProgressEffects() {
    const container = document.getElementById('timelineContainer');
    const progressItems = container.querySelectorAll('.timeline-item.progress.active');
    progressItems.forEach(item => {
        item.classList.remove('active');
    });
}

// 更新时间轴项状态（从 progress 变为 completed 或 error，移除光影效果）
function updateTimelineItemStatus(newType) {
    const container = document.getElementById('timelineContainer');
    const progressItems = container.querySelectorAll('.timeline-item.progress');
    
    progressItems.forEach(item => {
        // 移除 progress 类、active 类和相关动画
        item.classList.remove('progress', 'active');
        item.classList.add(newType);
        item.style.animation = 'none';
    });
}

// 添加时间轴项目
function addTimelineItem(type, title, message, timestamp) {
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
    
    item.innerHTML = `
        <div class="bg-gray-50 rounded-lg p-3">
            <div class="flex items-center justify-between mb-1">
                <h4 class="text-sm font-semibold text-gray-900">${title}</h4>
                <span class="text-xs text-gray-500">${time}</span>
            </div>
            <p class="text-xs text-gray-600">${message}</p>
        </div>
    `;
    
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

// 下载 PPT（全局函数，供 onclick 调用）
window.downloadPPT = function() {
    if (currentTaskId) {
        window.open(`${API_BASE}/ppt/tasks/${currentTaskId}/download`, '_blank');
    }
};

// 初始化函数
function initApp() {
    // 初始化示例提示词
    renderExamplePrompts();
    
    // 当用户输入 promptInput 时，清空错误消息
    const promptInput = document.getElementById('promptInput');
    if (promptInput) {
        promptInput.addEventListener('input', () => {
            const errorDiv = document.getElementById('promptError');
            if (errorDiv) {
                errorDiv.classList.add('hidden');
            }
        });
    }
    
    // 自定义人群选择
    const audienceSelect = document.getElementById('audienceSelect');
    if (audienceSelect) {
        audienceSelect.addEventListener('change', (e) => {
            const customInput = document.getElementById('customAudienceInput');
            if (customInput) {
                if (e.target.value === 'custom') {
                    customInput.classList.remove('hidden');
                } else {
                    customInput.classList.add('hidden');
                }
            }
        });
    }
    
    // 样式选择框图标更新
    const styleSelect = document.getElementById('styleSelect');
    if (styleSelect) {
        updateStyleIcon(); // 初始化图标
        styleSelect.addEventListener('change', updateStyleIcon);
    }
    
    // 初始化 WebSocket 连接
    initWebSocket();
}

// 初始化：检查文档是否已加载完成
// 如果文档已经加载完成（readyState 为 'complete' 或 'interactive'），直接执行初始化
// 否则等待 DOMContentLoaded 事件
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    // 文档已经加载完成，直接执行初始化
    // 使用 setTimeout 确保 DOM 元素都已渲染
    setTimeout(initApp, 0);
}
