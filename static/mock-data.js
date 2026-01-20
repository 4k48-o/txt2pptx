/**
 * Mock 数据 - 用于前端调试
 * 基于真实的后台日志生成
 */

// /manus 子路径部署适配：自动推断 base path
const APP_BASE = window.location.pathname.startsWith('/manus') ? '/manus' : '';

// Mock WebSocket 消息序列
const mockWebSocketMessages = [
    // 1. WebSocket 连接成功
    {
        type: 'connected',
        timestamp: '2026-01-16T10:22:10.208Z'
    },
    
    // 2. 任务创建事件
    {
        type: 'task_created',
        task_id: 'QqxM2dk9pVHxNGBTSqLoAe',
        local_task_id: 'e57e342f-ee5f-4240-8396-ccb09e77f612',
        title: 'Cybersecurity Training Module for Executives',
        task_url: 'https://manus.im/app/QqxM2dk9pVHxNGBTSqLoAe',
        message: '任务已创建，正在处理中...',
        timestamp: '2026-01-16T10:22:21.918Z'
    },
    
    // 3. 任务进度更新 1
    {
        type: 'task_progress',
        task_id: 'QqxM2dk9pVHxNGBTSqLoAe',
        message: 'Prepare slide content for cybersecurity training module',
        timestamp: '2026-01-16T10:22:29.923Z'
    },
    
    // 4. 任务进度更新 2
    {
        type: 'task_progress',
        task_id: 'QqxM2dk9pVHxNGBTSqLoAe',
        message: 'Generate slides presentation',
        timestamp: '2026-01-16T10:22:47.426Z'
    },
    
    // 5. 任务进度更新 3
    {
        type: 'task_progress',
        task_id: 'QqxM2dk9pVHxNGBTSqLoAe',
        message: 'Deliver final presentation to user',
        timestamp: '2026-01-16T10:25:16.979Z'
    },
    
    // 6. 任务完成
    {
        type: 'task_completed',
        task_id: 'QqxM2dk9pVHxNGBTSqLoAe',
        local_task_id: 'e57e342f-ee5f-4240-8396-ccb09e77f612',
        title: 'Cybersecurity Training Module for Executives',
        download_url: `${APP_BASE}/api/tasks/e57e342f-ee5f-4240-8396-ccb09e77f612/download`,
        message: 'PPT 生成完成！',
        timestamp: '2026-01-16T10:26:02.097Z'
    }
];

// Mock 任务创建响应（导出到全局，避免重复声明）
window.mockCreateTaskResponse = {
    success: true,
    data: {
        id: 'e57e342f-ee5f-4240-8396-ccb09e77f612',
        status: 'running',
        message: 'Task created, waiting for Manus webhook callback'
    },
    message: '任务创建成功，等待 Manus 处理'
};

/**
 * Mock WebSocket 类
 * 模拟真实的 WebSocket 行为
 */
class MockWebSocket {
    constructor(url) {
        this.url = url;
        this.readyState = WebSocket.CONNECTING;
        this.onopen = null;
        this.onmessage = null;
        this.onerror = null;
        this.onclose = null;
        
        // 模拟连接延迟
        setTimeout(() => {
            this.readyState = WebSocket.OPEN;
            if (this.onopen) {
                this.onopen({ type: 'open' });
            }
            
            // 发送连接成功消息
            this._sendMessage({
                type: 'connected',
                timestamp: new Date().toISOString()
            });
            
            // 开始发送 mock 消息序列
            this._startMockMessages();
        }, 100);
    }
    
    send(data) {
        console.log('[Mock WebSocket] Send:', data);
        // 模拟订阅响应
        try {
            const message = JSON.parse(data);
            if (message.action === 'subscribe') {
                console.log('[Mock WebSocket] Subscribed to task:', message.task_id);
            }
        } catch (e) {
            // 忽略解析错误
        }
    }
    
    close() {
        this.readyState = WebSocket.CLOSED;
        if (this.onclose) {
            this.onclose({ type: 'close' });
        }
    }
    
    _sendMessage(message) {
        if (this.onmessage && this.readyState === WebSocket.OPEN) {
            setTimeout(() => {
                this.onmessage({
                    data: JSON.stringify(message)
                });
            }, 50);
        }
    }
    
    _startMockMessages() {
        let index = 0;
        const delays = [
            222500,   // task_created 延迟 500ms
            228000,  // 第一个 progress 延迟 8秒
            218000, // 第二个 progress 延迟 18秒
            2150000, // 第三个 progress 延迟 150秒（2.5分钟）
            210000  // task_completed 延迟 10秒
        ];
        
        // 发送任务创建消息
        setTimeout(() => {
            if (index < mockWebSocketMessages.length) {
                this._sendMessage(mockWebSocketMessages[index]);
                index++;
            }
        }, delays[0]);
        
        // 发送进度更新消息
        delays.slice(1).forEach((delay, i) => {
            setTimeout(() => {
                if (index < mockWebSocketMessages.length) {
                    this._sendMessage(mockWebSocketMessages[index]);
                    index++;
                }
            }, delays[0] + delay);
        });
    }
}

/**
 * Mock API 响应
 */
const mockAPI = {
    async createTask(prompt, clientId) {
        console.log('[Mock API] Creating task:', prompt);
        
        // 模拟 API 延迟
        await new Promise(resolve => setTimeout(resolve, 500));
        
        return {
            ok: true,
            json: async () => mockCreateTaskResponse
        };
    }
};

/**
 * 启用 Mock 模式
 * 替换真实的 WebSocket 和 fetch
 */
function enableMockMode() {
    console.log('[Mock] 启用 Mock 模式');
    
    // 保存原始的 WebSocket
    window.RealWebSocket = WebSocket;
    
    // 替换 WebSocket
    window.WebSocket = MockWebSocket;
    
    // 保存原始的 fetch
    window.realFetch = window.fetch;
    
    // 替换 fetch（仅替换任务创建 API）
    window.fetch = function(url, options) {
        if (options && options.method === 'POST' && url.includes('/api/v2/tasks')) {
            const body = JSON.parse(options.body);
            return mockAPI.createTask(body.prompt, body.client_id);
        }
        // 其他请求使用真实的 fetch
        return window.realFetch.apply(this, arguments);
    };
    
    console.log('[Mock] Mock 模式已启用');
}

/**
 * 禁用 Mock 模式
 */
function disableMockMode() {
    console.log('[Mock] 禁用 Mock 模式');
    
    if (window.RealWebSocket) {
        window.WebSocket = window.RealWebSocket;
    }
    
    if (window.realFetch) {
        window.fetch = window.realFetch;
    }
    
    console.log('[Mock] Mock 模式已禁用');
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        mockWebSocketMessages,
        mockCreateTaskResponse,
        MockWebSocket,
        enableMockMode,
        disableMockMode
    };
}
